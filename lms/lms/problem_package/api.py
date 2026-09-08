"""Private import records and immutable versions. Publishing is capability-gated."""

import hashlib
import html
import json
import math

import frappe
import requests
from frappe.utils import add_days, now_datetime

from lms.lms.problem_package.parser import PackageError, preflight, read_archive
from lms.lms.problem_package.permissions import INTERNAL_WRITE

IMPORT = "LMS Problem Package Import"
VERSION = "LMS Problem Package Version"
EXERCISE = "LMS Programming Exercise"
PROTOCOL = "icpc-legacy-v1"


def _json(value):
	return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _enabled():
	if not frappe.conf.get("enable_icpc_problem_packages"):
		frappe.throw("ICPC package imports are disabled.")


def _manage(target=None):
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	if target:
		frappe.get_doc(EXERCISE, target).check_permission("write")
	elif not frappe.has_permission(EXERCISE, "create"):
		raise frappe.PermissionError


def _save(doc):
	doc.flags.package_service = INTERNAL_WRITE
	return doc.save(ignore_permissions=True)


def _owned(import_id):
	doc = frappe.get_doc(IMPORT, import_id)
	if doc.owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		raise frappe.PermissionError
	_manage(doc.target_exercise)
	return doc


def _content(doc):
	file = frappe.get_doc("File", doc.file_id)
	if not file.is_private:
		frappe.throw("The original package must remain private.")
	if (file.file_size or 0) > 20 * 1024 * 1024:
		frappe.throw("Package exceeds 20 MiB upload capacity.")
	content = file.get_content()
	if not isinstance(content, bytes):
		frappe.throw("Expected a binary ZIP file.")
	if doc.sha256 and hashlib.sha256(content).hexdigest() != doc.sha256:
		frappe.throw("The uploaded package has changed. Create a new import.")
	return content


@frappe.whitelist()
def create_import(file_id: str, target_exercise: str | None = None, allow_flat: bool = False):
	_enabled()
	_manage(target_exercise)
	file = frappe.get_doc("File", file_id)
	file.check_permission("read")
	if file.owner != frappe.session.user or not file.is_private:
		frappe.throw("Upload your own private package file.", frappe.PermissionError)
	if not file.file_name.lower().endswith((".zip", ".kpp")):
		frappe.throw("Expected a .zip or .kpp package.")
	doc = frappe.get_doc(
		{
			"doctype": IMPORT,
			"file_id": file_id,
			"target_exercise": target_exercise,
			"allow_flat": int(str(allow_flat).lower() in {"1", "true"}),
			"status": "Queued",
			"expires_at": add_days(now_datetime(), 7),
		}
	)
	content = _content(doc)
	if len(content) > 20 * 1024 * 1024:
		frappe.throw("Package exceeds 20 MiB upload capacity.")
	doc.sha256 = hashlib.sha256(content).hexdigest()
	_save(doc)
	frappe.enqueue(
		"lms.lms.problem_package.api.inspect_import",
		import_id=doc.name,
		queue="long",
		enqueue_after_commit=True,
	)
	return {"name": doc.name, "status": doc.status}


def inspect_import(import_id):
	doc = frappe.get_doc(IMPORT, import_id)
	if doc.status != "Queued":
		return
	try:
		report = preflight(_content(doc), allow_flat=bool(doc.allow_flat))
		doc.status = "Rejected" if report["errors"] else "Ready"
		doc.report = _json(report)
	except (PackageError, ValueError) as exc:
		doc.status = "Rejected"
		doc.report = _json({"errors": [str(exc)], "warnings": []})
	except Exception:
		frappe.log_error(title="ICPC package preflight failed", message=frappe.get_traceback())
		doc.status = "Rejected"
		doc.report = _json(
			{
				"errors": ["Preflight failed. Check the private server log and upload a new package."],
				"warnings": [],
			}
		)
	_save(doc)


@frappe.whitelist()
def get_import(import_id: str):
	doc = _owned(import_id)
	report = json.loads(doc.report or "{}")
	return {
		"name": doc.name,
		"status": doc.status,
		"package_version": doc.package_version,
		"title": report.get("title"),
		"format_version": report.get("format_version"),
		"errors": report.get("errors", []),
		"warnings": report.get("warnings", []),
		"validation_status": report.get("validation_status"),
		"statements": report.get("statements", []),
		"samples": [c for c in report.get("cases", []) if not c["hidden"]],
		"hidden_count": sum(c["hidden"] for c in report.get("cases", [])),
		"source": report.get("metadata", {}).get("source"),
		"memory_mib": report.get("metadata", {}).get("limits", {}).get("memory"),
		"allowed_languages": ["Python", "C++"],
	}


def require_capability(config=None, cases=None):
	from lms.lms.judge_service import _get_settings

	settings = _get_settings()
	try:
		response = requests.get(
			f"{settings.service_url.rstrip('/')}/internal/v1/capabilities",
			headers={"Authorization": f"Bearer {settings.get_password('api_token')}"},
			timeout=10,
		)
		response.raise_for_status()
		capability = response.json()
		if not isinstance(capability, dict):
			raise ValueError("Invalid capability response")
		if PROTOCOL not in capability.get("protocols", []):
			raise ValueError("Unsupported protocol")
		if config and config["memory_limit_kb"] < capability.get("min_memory_limit_kb", 16000):
			frappe.throw("Package memory limit is below the Judge0 deployment memory floor.")
		if config:
			if config["memory_limit_kb"] > capability.get("max_memory_limit_kb", 1024000):
				frappe.throw("Package memory limit exceeds the active Judge Service capacity.")
			if config.get("output_limit_bytes", 256000) > capability.get("max_output_bytes", 256000):
				frappe.throw("Package output limit exceeds the active Judge Service capacity.")
		if cases and any(len(case["input"].encode("utf-8")) > capability.get("max_input_bytes", 256000) for case in cases):
			frappe.throw("Package input size exceeds the active Judge Service capacity.")
		if capability.get("icpc_default_comparator_verified") is not True:
			raise ValueError("Comparator differential validation is missing")
	except (requests.RequestException, ValueError):
		frappe.throw(
			"Judge Service has not advertised verified icpc-legacy-v1 support. Publishing is blocked."
		)


@frappe.whitelist()
def commit_import(import_id: str, expected_target_version: str = "", options: dict | str | None = None):
	_enabled()
	doc = _owned(import_id)
	frappe.db.get_value(IMPORT, doc.name, "name", for_update=True)
	doc.reload()
	options = frappe.parse_json(options or {})
	if not isinstance(options, dict):
		frappe.throw("Expected import options.")
	if doc.package_version:
		previous = frappe.get_doc(VERSION, doc.package_version)
		config = json.loads(previous.judge_config)
		try:
			matching = (
				options.get("language") == config["language"]
				and options.get("statement_path") == previous.statement_path
				and float(options.get("time_limit_seconds")) == config["time_limit_seconds"]
				and float(options.get("memory_limit_kb")) == config["memory_limit_kb"]
			)
		except (TypeError, ValueError):
			matching = False
		if not matching:
			frappe.throw("This import was already confirmed with different options.")
		return {"version": doc.package_version, "exercise": previous.exercise}
	if doc.status != "Ready" or now_datetime() > frappe.utils.get_datetime(doc.expires_at):
		frappe.throw("Import is not ready or has expired.")
	report = preflight(_content(doc), allow_flat=bool(doc.allow_flat))
	if report["errors"] or _json(report) != doc.report:
		frappe.throw("Preflight artifacts changed; create a new import.")
	try:
		seconds = float(options["time_limit_seconds"])
		memory = int(options["memory_limit_kb"])
	except (KeyError, ValueError, TypeError):
		frappe.throw("Confirm actual time in seconds and memory in KiB.")
	if not math.isfinite(seconds) or not 0 < seconds <= 30 or not 16000 <= memory <= 1048576:
		frappe.throw("Execution limits exceed Judge Service capacity.")
	package_memory = report["metadata"].get("limits", {}).get("memory")
	if package_memory is not None and memory != package_memory * 1024:
		frappe.throw("Memory must match the package's MiB limit converted to KiB.")
	language = options.get("language")
	statement = options.get("statement_path")
	if language not in {"Python", "C++"} or statement not in report["statements"]:
		frappe.throw("Choose a supported language and PDF statement.")
	config = {
		"protocol_version": PROTOCOL,
		"comparison_mode": "icpc_default",
		"validator_flags": [],
		"scoring_mode": "icpc",
		"feedback_policy": "strict",
		"language": language,
		"time_limit_seconds": seconds,
		"time_limit_source": "teacher_confirmed",
		"memory_limit_kb": memory,
		"output_limit_bytes": int(report["metadata"].get("limits", {}).get("output", 256000 / (1024 * 1024)) * 1024 * 1024),
	}
	if doc.target_exercise:
		exercise = frappe.get_doc(EXERCISE, doc.target_exercise)
		if (exercise.active_package_version or "") != (expected_target_version or ""):
			frappe.throw("Exercise version changed. Refresh before confirming.")
	else:
		exercise = None
	confirmation_key = hashlib.sha256(
		_json([frappe.session.user, doc.target_exercise, doc.sha256, config, statement]).encode()
	).hexdigest()
	existing = frappe.db.get_value(VERSION, {"confirmation_key": confirmation_key}, "name")
	if existing:
		doc.package_version, doc.status = existing, "Committed"
		_save(doc)
		return {"version": existing}
	version = frappe.get_doc(
		{
			"doctype": VERSION,
			"confirmation_key": confirmation_key,
			"exercise": exercise.name if exercise else None,
			"import_record": doc.name,
			"source_uuid": report["metadata"].get("uuid"),
			"format_version": report["format_version"],
			"revision": frappe.db.count(VERSION, {"exercise": exercise.name}) + 1 if exercise else 1,
			"status": "Draft",
			"validation_status": report["validation_status"],
			"metadata": _json(report["metadata"]),
			"manifest": _json(report["manifest"]),
			"cases": _json(report["cases"]),
			"judge_config": _json(config),
			"config_digest": hashlib.sha256(_json(config).encode()).hexdigest(),
			"statement_path": statement,
			"expected_target_version": expected_target_version or "",
		}
	)
	_save(version)
	doc.package_version, doc.status = version.name, "Committed"
	_save(doc)
	return {"version": version.name, "exercise": version.exercise}


@frappe.whitelist()
def publish_version(version_id: str):
	_enabled()
	version = frappe.get_doc(VERSION, version_id)
	_manage(version.exercise)
	_owned(version.import_record)
	require_capability(json.loads(version.judge_config), json.loads(version.cases))
	frappe.db.get_value(VERSION, version.name, "name", for_update=True)
	version.reload()
	if version.exercise:
		frappe.db.get_value(EXERCISE, version.exercise, "name", for_update=True)
		exercise = frappe.get_doc(EXERCISE, version.exercise)
	else:
		exercise = frappe.new_doc(EXERCISE)
	if exercise.active_package_version == version.name:
		return {"exercise": exercise.name, "exercise_number": exercise.exercise_number, "version": version.name}
	if version.status != "Draft" or (exercise.active_package_version or "") != (
		version.expected_target_version or ""
	):
		frappe.throw("Concurrent publication detected. Import against the current version.")
	_content(frappe.get_doc(IMPORT, version.import_record))
	config, cases = json.loads(version.judge_config), json.loads(version.cases)
	exercise.flags.package_service = INTERNAL_WRITE
	exercise.source_type, exercise.active_package_version = "icpc", version.name
	exercise.scoring_mode, exercise.feedback_policy = "icpc", "strict"
	exercise.evaluation_mode = "Judge Service"
	exercise.language = config["language"]
	exercise.time_limit_seconds, exercise.memory_limit_kb = (
		config["time_limit_seconds"],
		config["memory_limit_kb"],
	)
	metadata = json.loads(version.metadata)
	exercise.title = metadata.get("name") or exercise.title or "Imported programming exercise"
	url = "/api/method/lms.lms.problem_package.api.download_statement?version_id=" + version.name
	exercise.problem_statement = (
		f'<p><a href="{html.escape(url, quote=True)}" target="_blank">Download PDF statement</a></p>'
	)
	exercise.set(
		"test_cases",
		[{"input": c["input"], "expected_output": c["expected_output"]} for c in cases if not c["hidden"]],
	)
	exercise.save()
	version.exercise = exercise.name
	version.status = "Published"
	_save(version)
	return {"exercise": exercise.name, "exercise_number": exercise.exercise_number, "version": version.name}


@frappe.whitelist()
def download_statement(version_id: str):
	version = frappe.get_doc(VERSION, version_id)
	exercise = frappe.get_doc(EXERCISE, version.exercise)
	exercise.check_permission("read")
	if frappe.session.user == "Guest" or exercise.active_package_version != version.name:
		_manage(version.exercise)
	doc = frappe.get_doc(IMPORT, version.import_record)
	files = read_archive(_content(doc))
	path = version.statement_path
	if path not in files:
		root = next(iter(files)).split("/")[0]
		path = root + "/" + path
	frappe.local.response.filename = "statement.pdf"
	frappe.local.response.filecontent = files[path]
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "attachment"


@frappe.whitelist()
def preview_statement(import_id: str, statement_path: str):
	doc = _owned(import_id)
	report = json.loads(doc.report or "{}")
	if statement_path not in report.get("statements", []):
		frappe.throw("Choose an available PDF statement.")
	files = read_archive(_content(doc))
	path = (
		statement_path if statement_path in files else next(iter(files)).split("/")[0] + "/" + statement_path
	)
	frappe.local.response.filename = "statement.pdf"
	frappe.local.response.filecontent = files[path]
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "attachment"
