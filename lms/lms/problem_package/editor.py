"""Teacher editing and private test-data transfer using new immutable versions."""

import copy
import hashlib
import io
import json
import zipfile

import frappe
import yaml
from frappe.utils import add_days, now_datetime

from lms.lms.problem_package import api
from lms.lms.problem_package.parser import DEFAULT_LIMITS, PackageError, preflight, read_archive


def _exercise(name, modified=None):
	api._manage(name)
	frappe.db.get_value(api.EXERCISE, name, "name", for_update=True)
	doc = frappe.get_doc(api.EXERCISE, name)
	if modified is not None and str(doc.modified) != modified:
		frappe.throw("Exercise changed. Refresh before saving.")
	return doc


def _cases(doc):
	if doc.source_type == "icpc":
		version = frappe.get_doc(api.VERSION, doc.active_package_version)
		return [case for case in json.loads(version.cases) if case["hidden"]]
	return frappe.get_all("LMS Judge Test Case", filters={"exercise": doc.name, "hidden": 1},
		fields=["input", "expected_output"], order_by="creation asc", limit_page_length=0)


def validate_cases(cases):
	if not isinstance(cases, list) or len(cases) > DEFAULT_LIMITS.cases:
		raise PackageError("Expected at most 100 test cases")
	total = 0
	for case in cases:
		if not isinstance(case, dict):
			raise PackageError("Invalid test case")
		for field in ("input", "expected_output"):
			value = case.get(field)
			if not isinstance(value, str) or "\x00" in value:
				raise PackageError("Test cases must contain UTF-8 text without NUL bytes")
			size = len(value.encode("utf-8"))
			if size > DEFAULT_LIMITS.file_bytes:
				raise PackageError("Test data exceeds 16 MiB per file")
			total += size
	if total > DEFAULT_LIMITS.total_bytes:
		raise PackageError("Test data exceeds 128 MiB")
	return cases


def hidden_zip(cases):
	output = io.BytesIO()
	with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		for index, case in enumerate(cases, 1):
			for field, extension in (("input", "in"), ("expected_output", "ans")):
				archive.writestr(f"data/secret/{index:03d}.{extension}", case[field])
	return output.getvalue()


def parse_hidden_zip(content):
	files = read_archive(content)
	# Accept our exported ZIP or flat .in/.ans pairs.
	if not files or any(not path.endswith((".in", ".ans")) for path in files):
		raise PackageError("Upload a ZIP containing only paired .in and .ans files")
	cases = []
	for path in sorted(files):
		if path.endswith(".ans"):
			if path[:-4] + ".in" not in files:
				raise PackageError(f"Missing input pair: {path}")
			continue
		answer = path[:-3] + ".ans"
		if answer not in files:
			raise PackageError(f"Missing answer pair: {path}")
		try:
			cases.append({"input": files[path].decode("utf-8"), "expected_output": files[answer].decode("utf-8")})
		except UnicodeError as exc:
			raise PackageError("Test data must be UTF-8") from exc
	return validate_cases(cases)


def rebuild_package(content, title, samples, hidden, statement_source=None, description=None):
	"""Preserve unrelated source files and executable modes when replacing data."""
	validate_cases(samples + hidden)
	files = read_archive(content)
	root = "" if "problem.yaml" in files else next(iter(files)).split("/")[0] + "/"
	metadata = yaml.safe_load(files[root + "problem.yaml"].decode("utf-8"))
	metadata["name"] = title
	replacements = {root + "problem.yaml": yaml.safe_dump(metadata, allow_unicode=True).encode()}
	if description is not None:
		replacements[root + "lms/statement.html"] = description.encode("utf-8")
	if statement_source is not None:
		replacements[root + "problem_statement/problem.tex"] = statement_source.encode("utf-8")
	for group, cases in (("sample", samples), ("secret", hidden)):
		for index, case in enumerate(cases, 1):
			for field, extension in (("input", "in"), ("expected_output", "ans")):
				value = case[field].replace("\r\n", "\n").replace("\r", "\n").removeprefix("\ufeff")
				if value and not value.endswith("\n"):
					value += "\n"
				replacements[f"{root}data/{group}/{index:03d}.{extension}"] = value.encode("utf-8")
	output = io.BytesIO()
	with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
		for entry in source.infolist():
			if entry.filename.startswith(root + "data/") or entry.filename in replacements or entry.filename == root + "lms/statement.html":
				continue
			target.writestr(copy.copy(entry), source.read(entry))
		for path, data in replacements.items():
			target.writestr(path, data)
	return output.getvalue()


def _save_package(doc, title, samples, hidden, statement_source, description):
	api._enabled()
	previous = frappe.get_doc(api.VERSION, doc.active_package_version)
	record = frappe.get_doc(api.IMPORT, previous.import_record)
	content = rebuild_package(api._content(record), title, samples, hidden, statement_source,
		description if statement_source is None and previous.statement_path.endswith(".pdf") else None)
	report = preflight(content, allow_flat=bool(record.allow_flat))
	if report["errors"]:
		frappe.throw("; ".join(report["errors"]))
	config = json.loads(previous.judge_config)
	api.require_capability(config, report["cases"])
	file = frappe.get_doc({"doctype": "File", "file_name": "edited-problem.zip", "is_private": 1,
		"content": content}).save(ignore_permissions=True)
	new_import = frappe.get_doc({"doctype": api.IMPORT, "file_id": file.name,
		"target_exercise": doc.name, "allow_flat": record.allow_flat, "status": "Ready",
		"sha256": hashlib.sha256(content).hexdigest(), "report": api._json(report),
		"expires_at": add_days(now_datetime(), 7)})
	api._save(new_import)
	result = api.commit_import(new_import.name, doc.active_package_version, {
		"language": config["language"], "statement_path": "problem_statement/problem.tex" if statement_source is not None else previous.statement_path,
		"time_limit_seconds": config["time_limit_seconds"], "memory_limit_kb": config["memory_limit_kb"]})
	api.publish_version(result["version"])


@frappe.whitelist(methods=["POST"])
def save_exercise(exercise: str, modified: str, title: str, problem_statement: str,
		test_cases: list | str, statement_source: str | None = None):
	doc = _exercise(exercise, modified)
	if not isinstance(problem_statement, str) or len(problem_statement.encode("utf-8")) > DEFAULT_LIMITS.file_bytes:
		frappe.throw("Invalid or oversized problem statement.")
	if statement_source is not None and (not isinstance(statement_source, str) or len(statement_source.encode("utf-8")) > DEFAULT_LIMITS.file_bytes):
		frappe.throw("Invalid or oversized TeX source.")
	samples = validate_cases(frappe.parse_json(test_cases))
	if not isinstance(title, str) or not title.strip():
		frappe.throw("Title is required.")
	if doc.source_type == "icpc":
		_save_package(doc, title.strip(), samples, _cases(doc), statement_source, problem_statement)
	else:
		doc.title, doc.problem_statement = title.strip(), problem_statement
		doc.set("test_cases", samples)
		doc.save()
	return {"exercise": doc.name}


@frappe.whitelist()
def download_hidden_cases(exercise: str):
	doc = _exercise(exercise)
	frappe.local.response.filename = f"{doc.exercise_number or doc.name}-hidden.zip"
	frappe.local.response.filecontent = hidden_zip(_cases(doc))
	frappe.local.response.type = "download"
	frappe.local.response.content_type = "application/zip"
	frappe.local.response_headers["Cache-Control"] = "private, no-store"


@frappe.whitelist()
def hidden_case_count(exercise: str):
	doc = _exercise(exercise)
	return len(_cases(doc))


@frappe.whitelist()
def preview_hidden_cases(exercise: str):
	doc = _exercise(exercise)
	return [{"input": case["input"][:2000], "expected_output": case["expected_output"][:2000],
		"truncated": len(case["input"]) > 2000 or len(case["expected_output"]) > 2000}
		for case in _cases(doc)]


@frappe.whitelist(methods=["POST"])
def upload_hidden_cases(exercise: str, modified: str, file_id: str):
	doc = _exercise(exercise, modified)
	file = frappe.get_doc("File", file_id)
	file.check_permission("read")
	if not file.is_private or file.owner != frappe.session.user:
		raise frappe.PermissionError
	if (file.file_size or 0) > DEFAULT_LIMITS.archive_bytes:
		frappe.throw("Package exceeds 20 MiB upload capacity.")
	cases = parse_hidden_zip(file.get_content())
	if doc.source_type == "icpc":
		# Keep the selected statement source while publishing new judge data.
		_save_package(doc, doc.title, [{"input": c.input, "expected_output": c.expected_output} for c in doc.test_cases],
			cases, None, doc.problem_statement)
	else:
		frappe.db.delete("LMS Judge Test Case", {"exercise": exercise, "hidden": 1})
		for case in cases:
			frappe.get_doc({"doctype": "LMS Judge Test Case", "exercise": exercise, "hidden": 1, **case}).insert()
		doc.save()
	return {"count": len(cases)}
