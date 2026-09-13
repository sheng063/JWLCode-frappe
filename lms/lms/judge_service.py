import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import urlparse

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, get_url
from lms.lms.problem_package.permissions import INTERNAL_WRITE


TERMINAL_STATUSES = {
	"ACCEPTED", "WRONG_ANSWER", "TIME_LIMIT_EXCEEDED", "MEMORY_LIMIT_EXCEEDED",
	"COMPILE_ERROR", "RUNTIME_ERROR", "SYSTEM_ERROR", "CANCELED", "OUTPUT_LIMIT_EXCEEDED", "CONNECTION_TIMEOUT",
}
SUPPORTED_LANGUAGES = {"Python", "C++"}

STATUS_LABELS = {
	"QUEUED": "Queued", "COMPILING": "Compiling", "RUNNING": "Running",
	"ACCEPTED": "Passed", "WRONG_ANSWER": "Failed",
	"TIME_LIMIT_EXCEEDED": "Time Limit Exceeded",
	"MEMORY_LIMIT_EXCEEDED": "Memory Limit Exceeded",
	"COMPILE_ERROR": "Compilation Error", "RUNTIME_ERROR": "Runtime Error",
	"SYSTEM_ERROR": "System Error", "CANCELED": "Canceled",
	"OUTPUT_LIMIT_EXCEEDED": "Output Limit Exceeded", "CONNECTION_TIMEOUT": "Connection Timeout",
}


def _get_settings():
	settings = frappe.get_single("LMS Judge Settings")
	if not settings.enabled:
		frappe.throw(_("Judge Service is not enabled."), frappe.ValidationError)
	parsed = urlparse(settings.service_url or "")
	if parsed.scheme not in {"http", "https"} or not parsed.netloc:
		frappe.throw(_("Judge Service URL is invalid."), frappe.ValidationError)
	return settings


def _validate_submission_access(exercise: str, code: str, language: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to submit code."), frappe.PermissionError)
	if not frappe.has_permission("LMS Programming Exercise", "read", exercise):
		frappe.throw(_("You do not have permission to access this exercise."), frappe.PermissionError)
	if language not in SUPPORTED_LANGUAGES:
		frappe.throw(_("Unsupported programming language."), frappe.ValidationError)
	if not isinstance(code, str) or not code.strip():
		frappe.throw(_("Source code is required."), frappe.ValidationError)
	if len(code.encode()) > 256_000:
		frappe.throw(_("Source code is too large."), frappe.ValidationError)


@frappe.whitelist()
def submit_programming_exercise(
	exercise: str, code: str, client_request_id: str, language: str = "Python", submission: str = "new"
):
	_validate_submission_access(exercise, code, language)
	if not isinstance(client_request_id, str) or not 8 <= len(client_request_id) <= 140:
		frappe.throw(_("A valid client request ID is required."), frappe.ValidationError)
	existing = frappe.db.get_value(
		"LMS Programming Exercise Submission",
		{"member": frappe.session.user, "client_request_id": client_request_id},
		"name",
	)
	if existing:
		return {"submission": existing, "status": frappe.db.get_value("LMS Programming Exercise Submission", existing, "status")}

	if submission == "new":
		doc = frappe.new_doc("LMS Programming Exercise Submission")
		doc.exercise = exercise
		doc.member = frappe.session.user
	else:
		doc = frappe.get_doc("LMS Programming Exercise Submission", submission)
		doc.check_permission("write")
		if doc.member != frappe.session.user or doc.exercise != exercise:
			frappe.throw(_("You cannot update this submission."), frappe.PermissionError)

	exercise_doc = frappe.get_doc("LMS Programming Exercise", exercise)
	package_version = exercise_doc.get("active_package_version")
	if package_version and submission != "new":
		frappe.throw("Create a new submission attempt for package exercises.")
	doc.package_version = package_version
	doc.attempt_id = str(uuid.uuid4())
	if package_version:
		version = frappe.get_doc("LMS Problem Package Version", package_version)
		doc.config_digest = version.config_digest
	doc.passed_tests = 0
	doc.total_tests = len(json.loads(version.cases)) if package_version else len(_test_cases(exercise_doc))
	doc.code = code
	doc.language = language
	doc.status = "Queued"
	doc.score = 0
	doc.client_request_id = client_request_id
	doc.judge_request_id = None
	doc.compiler_message = None
	doc.status_version = 0
	if package_version:
		doc.flags.package_service = INTERNAL_WRITE
	doc.save()
	frappe.enqueue(
		"lms.lms.judge_service.dispatch_submission",
		submission_name=doc.name,
		# Dispatch is a short HTTP request; never wait behind course indexing/imports.
		queue="short",
		enqueue_after_commit=True,
	)
	return {"submission": doc.name, "status": doc.status}


@frappe.whitelist()
def run_programming_exercise(exercise: str, code: str, language: str = "Python"):
	"""Run public examples without creating or updating a submission document."""
	_validate_submission_access(exercise, code, language)
	settings = _get_settings()
	exercise_doc = frappe.get_doc("LMS Programming Exercise", exercise)
	test_cases = [
		{"input": row.input or "", "expected_output": row.expected_output, "hidden": False}
		for row in exercise_doc.test_cases
	]
	if not test_cases:
		frappe.throw(_("At least one visible test case is required."), frappe.ValidationError)
	payload = {
		"language": language,
		"source_code": code,
		"time_limit_seconds": flt(exercise_doc.time_limit_seconds or 2),
		"memory_limit_kb": cint(exercise_doc.memory_limit_kb or 128000),
		"test_cases": test_cases,
	}
	if getattr(exercise_doc, "active_package_version", None):
		version = frappe.get_doc("LMS Problem Package Version", exercise_doc.active_package_version)
		from lms.lms.problem_package.api import require_capability
		require_capability()
		payload.update(_package_payload(version, public_only=True))
	_apply_submission_language(payload, language)
	response = requests.post(
		f"{settings.service_url.rstrip('/')}/internal/v1/runs",
		json=payload,
		headers={"Authorization": f"Bearer {settings.get_password('api_token')}"},
		timeout=max(cint(settings.request_timeout_seconds), 135),
	)
	response.raise_for_status()
	return response.json()


def _apply_submission_language(payload, language):
	"""Treat stored time limits as the C++ baseline for every execution path."""
	payload["language"] = language
	payload["time_limit_seconds"] = flt(payload["time_limit_seconds"]) * (1 if language == "C++" else 2)


def _package_payload(version, public_only=False):
	config = json.loads(version.judge_config)
	cases = json.loads(version.cases)
	return {key: config[key] for key in (
		"protocol_version", "comparison_mode", "validator_flags", "scoring_mode",
		"language", "time_limit_seconds", "memory_limit_kb"
	)} | {"output_limit_bytes": config.get("output_limit_bytes", 256000), "package_version": version.name, "config_digest": version.config_digest,
		"test_cases": [{key: c[key] for key in ("case_id", "input", "expected_output", "hidden")}
			for c in cases if not public_only or not c["hidden"]]}


def _test_cases(exercise):
	visible = [
		{"input": row.input or "", "expected_output": row.expected_output, "hidden": False}
		for row in exercise.test_cases
	]
	hidden = frappe.get_all(
		"LMS Judge Test Case",
		filters={"exercise": exercise.name},
		fields=["input", "expected_output", "hidden"],
		order_by="creation asc",
	)
	return visible + [
		{"input": row.input or "", "expected_output": row.expected_output, "hidden": bool(row.hidden)}
		for row in hidden
	]


def dispatch_submission(submission_name: str):
	doc = frappe.get_doc("LMS Programming Exercise Submission", submission_name)
	if doc.status not in {"Queued", "System Error"}:
		return
	settings = _get_settings()
	exercise = frappe.get_doc("LMS Programming Exercise", doc.exercise)
	test_cases = _test_cases(exercise) if not doc.get("package_version") else [True]
	if not test_cases:
		frappe.throw(_("At least one judge test case is required."), frappe.ValidationError)
	payload = {
		"submission_id": doc.name,
		"idempotency_key": f"{doc.name}:{doc.client_request_id}",
		"language": doc.language or "Python",
		"source_code": doc.code,
		"time_limit_seconds": flt(exercise.time_limit_seconds or 2),
		"memory_limit_kb": cint(exercise.memory_limit_kb or 128000),
		"test_cases": test_cases,
		"callback_url": settings.callback_url or get_url("/api/method/lms.lms.judge_service.judge_callback"),
	}
	if doc.get("package_version"):
		version = frappe.get_doc("LMS Problem Package Version", doc.package_version)
		payload.update(_package_payload(version))
		payload["attempt_id"] = doc.attempt_id
	_apply_submission_language(payload, doc.language or "Python")
	try:
		if doc.get("package_version"):
			from lms.lms.problem_package.api import require_capability
			require_capability()
		response = requests.post(
			f"{settings.service_url.rstrip('/')}/internal/v1/judge-requests",
			json=payload,
			headers={"Authorization": f"Bearer {settings.get_password('api_token')}"},
			timeout=max(cint(settings.request_timeout_seconds), 5),
		)
		response.raise_for_status()
		result = response.json()
		frappe.db.set_value(
			"LMS Programming Exercise Submission", doc.name,
			{"judge_request_id": result["judge_request_id"], "status": STATUS_LABELS.get(result["status"], "Queued")},
		)
	except Exception as exc:
		frappe.db.set_value(
			"LMS Programming Exercise Submission", doc.name,
			{"status": "System Error", "compiler_message": None if doc.get("package_version") else str(exc)[:2000]},
		)
		frappe.log_error(title="Judge Service dispatch failed", message=frappe.get_traceback())


def _verify_callback(body: bytes):
	settings = _get_settings()
	timestamp = frappe.get_request_header("X-JWL-Timestamp") or ""
	signature = frappe.get_request_header("X-JWL-Signature") or ""
	try:
		if abs(int(time.time()) - int(timestamp)) > 300:
			raise ValueError
	except ValueError:
		frappe.throw(_("Expired judge callback."), frappe.AuthenticationError)
	expected = hmac.new(
		settings.get_password("callback_secret").encode(),
		f"{timestamp}.".encode() + body,
		hashlib.sha256,
	).hexdigest()
	if not hmac.compare_digest(signature, f"sha256={expected}"):
		frappe.throw(_("Invalid judge callback signature."), frappe.AuthenticationError)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def judge_callback():
	body = frappe.request.get_data()
	_verify_callback(body)
	payload = json.loads(body)
	status = payload.get("status")
	if status not in STATUS_LABELS:
		frappe.throw(_("Unknown judge status."), frappe.ValidationError)
	doc = frappe.get_doc("LMS Programming Exercise Submission", payload.get("submission_id"))
	if doc.judge_request_id and doc.judge_request_id != payload.get("judge_request_id"):
		frappe.throw(_("Judge request does not match submission."), frappe.PermissionError)
	version = cint(payload.get("status_version"))
	if version <= cint(doc.status_version) or doc.event_id == payload.get("event_id"):
		return {"ok": True, "duplicate": True}
	_apply_result(doc, payload)
	return {"ok": True, "terminal": status in TERMINAL_STATUSES}


def _apply_result(doc, payload: dict):
	if getattr(doc, "package_version", None):
		frappe.db.get_value("LMS Programming Exercise Submission", doc.name, "name", for_update=True)
		doc.reload()
		version = frappe.get_doc("LMS Problem Package Version", doc.package_version)
		if (payload.get("package_version") != doc.package_version
			or payload.get("config_digest") != doc.config_digest
			or payload.get("attempt_id") != doc.attempt_id
			or payload.get("judge_request_id") != doc.judge_request_id):
			frappe.throw("Package result does not match this attempt.", frappe.PermissionError)
		known = {c["case_id"] for c in json.loads(version.cases)}
		returned = [c.get("case_id") for c in payload.get("cases", [])]
		if len(returned) != len(set(returned)) or not set(returned) <= known:
			frappe.throw("Unknown or duplicate case IDs in result.")
		if payload["status"] == "ACCEPTED" and (set(returned) != known or any(
			c.get("status") != "Accepted" for c in payload.get("cases", [])
		)):
			frappe.throw("Accepted result must include every accepted test case.")
		if cint(payload.get("status_version")) <= cint(doc.status_version):
			return
		if getattr(doc, "status", None) in {STATUS_LABELS[status] for status in TERMINAL_STATUSES}:
			return
	doc.judge_request_id = doc.judge_request_id or payload.get("judge_request_id")
	doc.status = STATUS_LABELS[payload["status"]]
	doc.status_version = cint(payload.get("status_version"))
	doc.event_id = payload.get("event_id")
	doc.passed_tests = sum(1 for case in payload.get("cases") or [] if case.get("status") == "Accepted")
	if getattr(doc, "package_version", None):
		doc.total_tests = len(known)
	elif payload.get("cases"):
		doc.total_tests = len(_test_cases(frappe.get_doc("LMS Programming Exercise", doc.exercise)))
	doc.score = flt(payload.get("score"))
	doc.time_ms = cint(payload.get("time_ms"))
	doc.memory_kb = cint(payload.get("memory_kb"))
	doc.compiler_message = payload.get("compiler_message")
	if getattr(doc, "package_version", None):
		doc.score = 100 if payload["status"] == "ACCEPTED" else 0
		# Never copy service diagnostics into student-readable package submissions.
		doc.compiler_message = None
	_record_first_failed_hidden_case(doc, payload)
	if getattr(doc, "package_version", None):
		doc.flags.package_service = INTERNAL_WRITE
	doc.save(ignore_permissions=True)


def _record_first_failed_hidden_case(doc, payload: dict):
	"""Persist only one failed hidden case as feedback for its submitter.

	The complete hidden suite stays in ``LMS Judge Test Case``. Submission
	children are readable by their owner, so retaining every failed case here
	would disclose the suite over repeated submissions.
	"""
	doc.set("test_cases", [])
	if getattr(doc, "package_version", None) or payload.get("status") == "ACCEPTED":
		return

	exercise = frappe.get_doc("LMS Programming Exercise", doc.exercise)
	all_cases = _test_cases(exercise)
	for result in payload.get("cases") or []:
		index = cint(result.get("index")) - 1
		if not 0 <= index < len(all_cases):
			continue
		case = all_cases[index]
		if not case["hidden"] or result.get("status") == "Accepted":
			continue
		doc.append(
			"test_cases",
			{
				"input": case["input"],
				"expected_output": case["expected_output"],
				"output": result.get("stdout") or "",
				"status": "Failed",
				"hidden": 1,
			},
		)
		return


def _refresh_from_judge_service(doc):
	if not doc.judge_request_id or doc.status not in {"Queued", "Compiling", "Running"}:
		return
	settings = _get_settings()
	try:
		response = requests.get(
			f"{settings.service_url.rstrip('/')}/internal/v1/judge-requests/{doc.judge_request_id}",
			headers={"Authorization": f"Bearer {settings.get_password('api_token')}"},
			timeout=max(cint(settings.request_timeout_seconds), 5),
		)
		response.raise_for_status()
		payload = response.json()
		if payload.get("status") in TERMINAL_STATUSES:
			payload.setdefault("status_version", cint(doc.status_version) + 1)
			payload.setdefault("event_id", f"poll:{doc.judge_request_id}:{payload['status_version']}")
			_apply_result(doc, payload)
		elif payload.get("status") in STATUS_LABELS:
			frappe.db.set_value(
				"LMS Programming Exercise Submission",
				doc.name,
				"status",
				STATUS_LABELS[payload["status"]],
				update_modified=False,
			)
	except requests.RequestException:
		return


@frappe.whitelist()
def get_programming_submission_status(submission: str):
	doc = frappe.get_doc("LMS Programming Exercise Submission", submission)
	doc.check_permission("read")
	_refresh_from_judge_service(doc)
	doc.reload()
	return {
		"name": doc.name, "status": doc.status, "score": doc.score,
		"time_ms": doc.time_ms, "memory_kb": doc.memory_kb,
		"compiler_message": doc.compiler_message,
	}
