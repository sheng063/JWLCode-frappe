"""Permission-checked bulk export of retained ICPC problem packages."""

import copy
import hashlib
import io
import json
import re
import zipfile

import frappe
from frappe import _

from lms.lms.problem_package.api import EXERCISE, IMPORT, VERSION, _content
from lms.lms.problem_package.parser import PackageError, preflight

MAX_EXERCISES = 50
MAX_TOTAL_BYTES = 100 * 1024 * 1024


def package_zip(content, package_name, *, allow_flat=False):
	"""Normalize the root while preserving file bytes and executable permissions."""
	report = preflight(content, allow_flat=allow_flat)
	if report["errors"]:
		raise PackageError("; ".join(report["errors"]))
	output = io.BytesIO()
	with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(output, "w") as target:
		flat = "problem.yaml" in source.namelist()
		for entry in source.infolist():
			if entry.is_dir():
				continue
			path = entry.filename if flat else entry.filename.split("/", 1)[1]
			if any(
				not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,253}[a-zA-Z0-9]", part)
				for part in path.split("/")
			):
				raise PackageError(f"Invalid ICPC filename: {path}")
			info = copy.copy(entry)
			info.filename = f"{package_name}/{path}"
			target.writestr(info, source.read(entry))
	return output.getvalue(), report


@frappe.whitelist(methods=["POST"])
def export_exercises(exercises: list[str] | str):
	"""Return one ZIP containing an independent ZIP for each selected exercise.

	Check the complete selection before reading any private files. A failed item
	fails the whole request; there is never a silently incomplete download.
	"""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	try:
		names = frappe.parse_json(exercises) if isinstance(exercises, str) else exercises
	except (ValueError, TypeError):
		frappe.throw(_("Expected a list of exercise IDs."))
	if (
		not isinstance(names, list)
		or not 1 <= len(names) <= MAX_EXERCISES
		or any(not isinstance(name, str) or not name.strip() or len(name) > 140 for name in names)
	):
		frappe.throw(_("Select between 1 and 50 exercises to export."))
	documents = []
	for name in dict.fromkeys(names):
		exercise = frappe.get_doc(EXERCISE, name)
		exercise.check_permission("read")
		exercise.check_permission("write")
		exercise.check_permission("export")
		documents.append(exercise)

	versions = []
	for exercise in documents:
		if exercise.source_type != "icpc" or not exercise.active_package_version:
			frappe.throw(
				_(
					"Exercise {0} has no complete ICPC package. Import a package containing a statement, secret data, accepted solution and input validator first."
				).format(exercise.title)
			)
		version = frappe.get_doc(VERSION, exercise.active_package_version)
		version.check_permission("read")
		if version.exercise != exercise.name or version.status != "Published":
			frappe.throw(_("Exercise {0} has an invalid active package version.").format(exercise.title))
		record = frappe.get_doc(IMPORT, version.import_record)
		record.check_permission("read")
		versions.append((exercise, version, record))

	output = io.BytesIO()
	manifest, total = [], 0
	with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
		for index, (exercise, version, record) in enumerate(versions, 1):
			content = _content(record)
			total += len(content)
			if total > MAX_TOTAL_BYTES:
				frappe.throw(_("Selected packages exceed 100 MiB. Export fewer exercises at a time."))
			package_name = f"p{index:03d}" + hashlib.sha256(exercise.name.encode()).hexdigest()[:12]
			try:
				package, report = package_zip(content, package_name, allow_flat=bool(record.allow_flat))
			except PackageError as exc:
				frappe.throw(_("Cannot export exercise {0}: {1}").format(exercise.title, str(exc)))
			bundle.writestr(package_name + ".zip", package)
			if output.tell() > MAX_TOTAL_BYTES:
				frappe.throw(_("Export exceeds 100 MiB. Export fewer exercises at a time."))
			manifest.append(
				{
					"exercise": exercise.name,
					"title": exercise.title,
					"file": package_name + ".zip",
					"package_version": version.name,
					"format_version": report["format_version"],
					"sha256": hashlib.sha256(package).hexdigest(),
					"judge_config": json.loads(version.judge_config),
					"validation_status": report["validation_status"],
					"warnings": report["warnings"],
				}
			)
		bundle.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
		bundle.writestr(
			"README.txt",
			(
				"Each ZIP is a separate legacy ICPC problem package.\n"
				"manifest.json maps filenames to exercises and their active versions.\n"
				"Original problem files, metadata and program permissions are preserved.\n"
				"LMS execution limits are recorded in judge_config in the manifest; legacy ICPC\n"
				"time multipliers are not absolute time limits in seconds.\n"
				"Structure checked; input validators and reference solutions were NOT executed.\n"
			),
		)
	if output.tell() > MAX_TOTAL_BYTES:
		frappe.throw(_("Export exceeds 100 MiB. Export fewer exercises at a time."))
	frappe.local.response.filename = "programming-exercises.zip"
	frappe.local.response.filecontent = output.getvalue()
	frappe.local.response.type = "download"
	frappe.local.response.content_type = "application/zip"
	frappe.local.response.display_content_as = "attachment"
	frappe.local.response_headers["Cache-Control"] = "private, no-store"
