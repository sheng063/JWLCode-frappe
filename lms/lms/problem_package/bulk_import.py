"""Bounded ZIP bundle ingestion, reusing the private single-package pipeline."""

import hashlib
import json
import re
from dataclasses import replace

import frappe
from frappe import _

from lms.lms.problem_package.api import IMPORT, _enabled, _manage, create_import
from lms.lms.problem_package.parser import DEFAULT_LIMITS, PackageError, read_archive

BUNDLE_BYTES = 100 * 1024 * 1024
MAX_PACKAGES = 50


def read_bundle(content):
	"""Expand exactly one bundle level; individual packages remain opaque ZIPs."""
	files = read_archive(
		content,
		replace(
			DEFAULT_LIMITS,
			archive_bytes=BUNDLE_BYTES,
			total_bytes=BUNDLE_BYTES,
			file_bytes=20 * 1024 * 1024,
			files=MAX_PACKAGES + 2,
		),
	)
	packages = {path: data for path, data in files.items() if path.lower().endswith((".zip", ".kpp"))}
	if not 1 <= len(packages) <= MAX_PACKAGES:
		raise PackageError("A bundle must contain between 1 and 50 problem ZIP/KPP files.")
	if any("/" in path or path not in {*packages, "manifest.json", "README.txt"} for path in files):
		raise PackageError(
			"Place problem ZIP/KPP files at the bundle root, with optional manifest.json and README.txt."
		)
	if any(
		not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,249}\.(?:zip|kpp)", path, re.IGNORECASE)
		for path in packages
	):
		raise PackageError(
			"Problem archive filenames must use letters, digits, dots, hyphens or underscores."
		)
	hints = {}
	if "manifest.json" in files:
		if len(files["manifest.json"]) > 1024 * 1024:
			raise PackageError("Bundle manifest exceeds 1 MiB.")
		try:
			manifest = json.loads(files["manifest.json"])
		except (ValueError, UnicodeError) as exc:
			raise PackageError("Invalid bundle manifest JSON.") from exc
		if not isinstance(manifest, list) or len(manifest) > MAX_PACKAGES:
			raise PackageError("Bundle manifest must be a list of at most 50 entries.")
		for entry in manifest:
			if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
				raise PackageError("Each manifest entry must name a problem file.")
			path = entry["file"]
			if path not in packages or path in hints:
				raise PackageError(f"Unknown or duplicate manifest file: {path}")
			if entry.get("sha256") and entry["sha256"] != hashlib.sha256(packages[path]).hexdigest():
				raise PackageError(f"Package checksum mismatch: {path}")
			config = entry.get("judge_config", {})
			if not isinstance(config, dict):
				raise PackageError(f"Invalid judge configuration: {path}")
			# These are reviewable hints only. commit_import validates every value.
			hints[path] = {
				key: config[key]
				for key in (
					"language",
					"time_limit_seconds",
					"memory_limit_kb",
				)
				if key in config and type(config[key]) in {str, int, float}
			}
	return [(path, data, hints.get(path, {})) for path, data in sorted(packages.items())]


@frappe.whitelist(methods=["POST"])
def create_bulk_import(file_id: str):
	_enabled()
	_manage()
	file = frappe.get_doc("File", file_id)
	file.check_permission("read")
	if file.owner != frappe.session.user or not file.is_private:
		frappe.throw(_("Upload your own private package file."), frappe.PermissionError)
	if not file.file_name.lower().endswith(".zip") or (file.file_size or 0) > BUNDLE_BYTES:
		frappe.throw(_("Upload a ZIP bundle no larger than 100 MiB."))
	content = file.get_content()
	if not isinstance(content, bytes):
		frappe.throw(_("Expected a binary ZIP file."))
	try:
		packages = read_bundle(content)
	except PackageError as exc:
		frappe.throw(_("Cannot import bundle: {0}").format(str(exc)))

	# Serialise retries for the same uploaded bundle. Child File attachments let a
	# retried request recover the existing import rather than create duplicate drafts.
	frappe.db.get_value("File", file.name, "name", for_update=True)
	results = []
	for path, data, options in packages:
		child_name = frappe.db.get_value(
			"File",
			{
				"attached_to_doctype": "File",
				"attached_to_name": file.name,
				"file_name": path,
				"owner": frappe.session.user,
				"is_private": 1,
			},
			"name",
		)
		if child_name:
			child = frappe.get_doc("File", child_name)
			if child.get_content() != data:
				frappe.throw(_("The uploaded bundle has changed. Upload a new file."))
		else:
			child = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": path,
					"is_private": 1,
					"content": data,
					"attached_to_doctype": "File",
					"attached_to_name": file.name,
				}
			).insert()
		import_id = frappe.db.get_value(IMPORT, {"file_id": child.name, "owner": frappe.session.user}, "name")
		if not import_id:
			import_id = create_import(child.name)["name"]
		results.append({"name": import_id, "filename": path, "options": options})
	return {"imports": results}
