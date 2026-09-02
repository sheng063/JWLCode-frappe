import hashlib
import hmac
import json
import time
from urllib.parse import urlparse

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, get_url


TERMINAL_STATUSES = {
	"ACCEPTED", "WRONG_ANSWER", "TIME_LIMIT_EXCEEDED", "MEMORY_LIMIT_EXCEEDED",
	"COMPILE_ERROR", "RUNTIME_ERROR", "SYSTEM_ERROR", "CANCELED",
}
STATUS_LABELS = {
	"QUEUED": "Queued", "COMPILING": "Compiling", "RUNNING": "Running",
	"ACCEPTED": "Passed", "WRONG_ANSWER": "Failed",
	"TIME_LIMIT_EXCEEDED": "Time Limit Exceeded",
	"MEMORY_LIMIT_EXCEEDED": "Memory Limit Exceeded",
	"COMPILE_ERROR": "Compilation Error", "RUNTIME_ERROR": "Runtime Error",
	"SYSTEM_ERROR": "System Error", "CANCELED": "Canceled",
}


def _get_settings():
	settings = frappe.get_single("LMS Judge Settings")
	if not settings.enabled:
		frappe.throw(_("Judge Service is not enabled."), frappe.ValidationError)
	parsed = urlparse(settings.service_url or "")
	if parsed.scheme not in {"http", "https"} or not parsed.netloc:
		frappe.throw(_("Judge Service URL is invalid."), frappe.ValidationError)
	return settings


def _validate_submission_access(exercise: str, code: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to submit code."), frappe.PermissionError)
	if not frappe.has_permission("LMS Programming Exercise", "read", exercise):
		frappe.throw(_("You do not have permission to access this exercise."), frappe.PermissionError)
	if not isinstance(code, str) or not code.strip():
		frappe.throw(_("Source code is required."), frappe.ValidationError)
	if len(code.encode()) > 256_000:
		frappe.throw(_("Source code is too large."), frappe.ValidationError)


@frappe.whitelist()
def submit_programming_exercise(exercise: str, code: str, client_request_id: str, submission: str = "new"):
	_validate_submission_access(exercise, code)
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

	doc.code = code
	doc.status = "Queued"
	doc.score = 0
	doc.client_request_id = client_request_id
	doc.judge_request_id = None
	doc.compiler_message = None
	doc.status_version = 0
	doc.save()
	frappe.enqueue(
		"lms.lms.judge_service.dispatch_submission",
		submission_name=doc.name,
		queue="long",
		enqueue_after_commit=True,
	)
	return {"submission": doc.name, "status": doc.status}


@frappe.whitelist()
def run_programming_exercise(exercise: str, code: str):
	"""Run public examples without creating or updating a submission document."""
	_validate_submission_access(exercise, code)
	settings = _get_settings()
	exercise_doc = frappe.get_doc("LMS Programming Exercise", exercise)
	test_cases = [
		{"input": row.input or "", "expected_output": row.expected_output, "hidden": False}
		for row in exercise_doc.test_cases
	]
	if not test_cases:
		frappe.throw(_("At least one visible test case is required."), frappe.ValidationError)
	payload = {
		"language": exercise_doc.language,
		"source_code": code,
		"time_limit_seconds": flt(exercise_doc.time_limit_seconds or 2),
		"memory_limit_kb": cint(exercise_doc.memory_limit_kb or 128000),
		"test_cases": test_cases,
	}
	response = requests.post(
		f"{settings.service_url.rstrip('/')}/internal/v1/runs",
		json=payload,
		headers={"Authorization": f"Bearer {settings.get_password('api_token')}"},
		timeout=max(cint(settings.request_timeout_seconds), 135),
	)
	response.raise_for_status()
	return response.json()


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
	test_cases = _test_cases(exercise)
	if not test_cases:
		frappe.throw(_("At least one judge test case is required."), frappe.ValidationError)
	payload = {
		"submission_id": doc.name,
		"idempotency_key": f"{doc.name}:{doc.client_request_id}",
		"language": exercise.language,
		"source_code": doc.code,
		"time_limit_seconds": flt(exercise.time_limit_seconds or 2),
		"memory_limit_kb": cint(exercise.memory_limit_kb or 128000),
		"test_cases": test_cases,
		"callback_url": settings.callback_url or get_url("/api/method/lms.lms.judge_service.judge_callback"),
	}
	try:
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
			{"status": "System Error", "compiler_message": str(exc)[:2000]},
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
	doc.judge_request_id = doc.judge_request_id or payload.get("judge_request_id")
	doc.status = STATUS_LABELS[payload["status"]]
	doc.status_version = cint(payload.get("status_version"))
	doc.event_id = payload.get("event_id")
	doc.score = flt(payload.get("score"))
	doc.time_ms = cint(payload.get("time_ms"))
	doc.memory_kb = cint(payload.get("memory_kb"))
	doc.compiler_message = payload.get("compiler_message")
	doc.save(ignore_permissions=True)


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
