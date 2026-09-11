"""Versioned course ZIPs with transactional ICPC publication and source-ID mapping."""

import hashlib
import json
import zipfile

import frappe
from frappe.utils import add_days, now_datetime

from lms.lms.problem_package import api as packages
from lms.lms.problem_package.export import package_zip
from lms.lms.problem_package.parser import preflight

FORMAT = "lms-course"
VERSION = 2
MAX_BYTES = 512 * 1024 * 1024


def write_programming_packages(archive, assessments):
	manifest = {"format": FORMAT, "version": VERSION, "programming_exercises": []}
	for assessment in assessments:
		if assessment["doctype"] != packages.EXERCISE:
			continue
		exercise = frappe.get_doc(packages.EXERCISE, assessment["name"])
		exercise.check_permission("write")  # Packages include protected judge data.
		entry = {"exercise": exercise.name, "source_type": exercise.source_type or "manual"}
		if exercise.source_type == "icpc":
			version = frappe.get_doc(packages.VERSION, exercise.active_package_version)
			if version.exercise != exercise.name or version.status != "Published":
				frappe.throw(f"Invalid active ICPC version for {exercise.title}.")
			record = frappe.get_doc(packages.IMPORT, version.import_record)
			root = "p" + hashlib.sha256(exercise.name.encode()).hexdigest()[:24]
			content, _ = package_zip(packages._content(record), root, allow_flat=bool(record.allow_flat))
			entry.update(
				{
					"file": f"programming/{root}.zip",
					"sha256": hashlib.sha256(content).hexdigest(),
					"options": {
						**{
							key: json.loads(version.judge_config)[key]
							for key in ("language", "time_limit_seconds", "memory_limit_kb")
						},
						"statement_path": version.statement_path,
					},
				}
			)
			archive.writestr(entry["file"], content)
		else:
			entry["hidden_test_cases"] = frappe.get_all(
				"LMS Judge Test Case",
				filters={"exercise": exercise.name},
				fields=["input", "expected_output", "hidden"],
				order_by="creation asc",
			)
		manifest["programming_exercises"].append(entry)
	archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))


def _json(archive, path, *, optional=False):
	if optional and path not in archive.namelist():
		return None
	try:
		return json.loads(archive.read(path))
	except (KeyError, ValueError, UnicodeError) as exc:
		frappe.throw(f"Invalid course ZIP entry {path}: {exc}")


def _documents(archive, directory):
	result = {}
	for path in archive.namelist():
		if not path.startswith(directory + "/") or not path.endswith(".json"):
			continue
		if "/" in path[len(directory) + 1 :]:
			continue
		doc = _json(archive, path)
		if not isinstance(doc, dict) or not isinstance(doc.get("name"), str) or not doc["name"]:
			frappe.throw(f"Missing document ID in {path}.")
		if doc["name"] in result and result[doc["name"]] != doc:
			frappe.throw(f"Conflicting document ID in {path}.")
		result[doc["name"]] = doc
	return result


def _clean(data):
	"""Never transfer ownership, child identities, or source parent links."""
	ignored = {
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"parent",
		"parenttype",
		"parentfield",
		"idx",
	}
	return {
		key: [_clean(row) if isinstance(row, dict) else row for row in value]
		if isinstance(value, list)
		else value
		for key, value in data.items()
		if key not in ignored
	}


def _insert(doctype, data):
	doc = frappe.new_doc(doctype)
	doc.update({key: value for key, value in _clean(data).items() if key != "doctype"})
	doc.insert(ignore_permissions=True)
	return doc


def _assessment_refs(content):
	from lms.lms.course_import_export import get_assessment_map
	from lms.lms.utils import get_editorjs_blocks

	for block in get_editorjs_blocks(content):
		kind = block.get("type")
		if kind in get_assessment_map():
			yield kind, (block.get("data") or {}).get("exercise" if kind == "program" else kind)


def _validate(archive):
	from lms.lms.course_import_export import export_lesson_type, get_assessment_map

	if sum(info.file_size for info in archive.infolist()) > MAX_BYTES:
		frappe.throw("Course ZIP exceeds 512 MiB uncompressed capacity.")
	course = _json(archive, "course.json")
	if not isinstance(course, dict):
		frappe.throw("Invalid course.json.")
	manifest = _json(archive, "manifest.json", optional=True)
	if manifest is not None and (
		not isinstance(manifest, dict)
		or manifest.get("format") != FORMAT
		or manifest.get("version") != VERSION
	):
		frappe.throw("Unsupported course ZIP format version.")
	chapters = _documents(archive, "chapters")
	lessons = _documents(archive, "lessons")
	assessments = _documents(archive, "assessments")
	for row in course.get("chapters", []):
		if row.get("chapter") not in chapters:
			frappe.throw("Course ZIP is missing a referenced chapter.")
	for chapter in chapters.values():
		for row in chapter.get("lessons", []):
			if row.get("lesson") not in lessons or lessons[row["lesson"]].get("chapter") != chapter["name"]:
				frappe.throw("Course ZIP has an invalid lesson reference.")
	for lesson in lessons.values():
		if lesson.get("chapter") not in chapters:
			frappe.throw("Course ZIP is missing the lesson's chapter.")
		lesson["lesson_type"] = export_lesson_type(lesson)
		for field in ("content", "instructor_content"):
			for kind, name in _assessment_refs(lesson.get(field)):
				if name not in assessments or assessments[name].get("doctype") != get_assessment_map()[kind]:
					frappe.throw(f"Lesson {lesson['title']} references missing {kind}: {name}.")
	entries = {}
	programs = (manifest or {}).get("programming_exercises", [])
	if not isinstance(programs, list):
		frappe.throw("Invalid programming package manifest.")
	for entry in programs:
		if (
			not isinstance(entry, dict)
			or entry.get("exercise") not in assessments
			or entry["exercise"] in entries
			or assessments[entry["exercise"]]["doctype"] != packages.EXERCISE
		):
			frappe.throw("Invalid or duplicate programming package mapping.")
		entries[entry["exercise"]] = entry
	for name, assessment in assessments.items():
		if assessment.get("doctype") not in get_assessment_map().values():
			frappe.throw("Unsupported assessment type in course ZIP.")
		if manifest is not None and assessment["doctype"] == packages.EXERCISE and name not in entries:
			frappe.throw(f"Missing programming package mapping for {name}.")
		if assessment.get("source_type") == "icpc" or assessment.get("active_package_version"):
			assessment["source_type"] = "icpc"
			entry = entries.get(name, {})
			path = entry.get("file", "")
			if (
				entry.get("source_type") != "icpc"
				or not path.startswith("programming/")
				or path not in archive.namelist()
			):
				frappe.throw(
					f"Missing ICPC package for {assessment['title']}. Export the course again with the new format."
				)
			if archive.getinfo(path).file_size > 20 * 1024 * 1024:
				frappe.throw("ICPC package exceeds 20 MiB.")
			content = archive.read(path)
			if hashlib.sha256(content).hexdigest() != entry.get("sha256"):
				frappe.throw(f"ICPC package checksum mismatch: {path}.")
			report = preflight(content)
			if report["errors"]:
				frappe.throw(f"Invalid ICPC package {assessment['title']}: " + "; ".join(report["errors"]))
	return course, chapters, lessons, assessments, entries


def _import_programs(archive, assessments, entries):
	mapping = {}
	for name, data in assessments.items():
		if data["doctype"] != packages.EXERCISE:
			continue
		entry = entries.get(name, {})
		if data.get("source_type") == "icpc":
			packages._enabled()
			packages._manage()
			content = archive.read(entry["file"])
			file = _insert(
				"File", {"file_name": entry["file"].split("/")[-1], "is_private": 1, "content": content}
			)
			# Synchronous inspection/publication in this request's transaction. No worker
			# may publish a partially imported course after this request has rolled back.
			record = frappe.get_doc(
				{
					"doctype": packages.IMPORT,
					"file_id": file.name,
					"sha256": hashlib.sha256(content).hexdigest(),
					"status": "Queued",
					"allow_flat": 0,
					"expires_at": add_days(now_datetime(), 7),
				}
			)
			packages._save(record)
			packages.inspect_import(record.name)
			version = packages.commit_import(record.name, options=entry.get("options"))
			published = packages.publish_version(version["version"])
			mapping[name] = published["exercise"]
		else:
			clean = dict(data)
			for key in ("exercise_number", "course", "lesson", "active_package_version"):
				clean.pop(key, None)
			doc = _insert(packages.EXERCISE, clean)
			mapping[name] = doc.name
			for case in entry.get("hidden_test_cases", []):
				_insert("LMS Judge Test Case", {**case, "exercise": doc.name})
	return mapping


def _import_assessments(archive, assessments, mapping):
	questions = {}
	for name, data in _documents(archive, "assessments/questions").items():
		questions[name] = _insert("LMS Question", data).name
	for name, data in assessments.items():
		if data["doctype"] == packages.EXERCISE:
			continue
		clean = dict(data)
		clean.pop("lesson", None)
		clean.pop("course", None)
		if data["doctype"] == "LMS Quiz":
			clean["questions"] = []
			for row in data.get("questions", []):
				if row.get("question") not in questions:
					frappe.throw("Course ZIP is missing a quiz question.")
				clean["questions"].append({**row, "question": questions[row["question"]]})
		mapping[name] = _insert(data["doctype"], clean).name


def _replace_references(content, mapping):
	from lms.lms.course_import_export import get_assessment_map

	try:
		parsed = json.loads(content)
	except (TypeError, ValueError):
		return content
	if not isinstance(parsed, dict):
		return content
	for block in parsed.get("blocks") or []:
		if not isinstance(block, dict) or block.get("type") not in get_assessment_map():
			continue
		field = "exercise" if block["type"] == "program" else block["type"]
		data = block.get("data")
		if not isinstance(data, dict) or data.get(field) not in mapping:
			frappe.throw("Missing imported assessment mapping.")
		data[field] = mapping[data[field]]
	return json.dumps(parsed, ensure_ascii=False)


def _import_assets(archive):
	manifest = _json(archive, "assets.json", optional=True)
	if manifest is None:
		# Older exports carry only basenames; retain their existing import support.
		manifest = [
			{"file": path, "file_name": path.rsplit("/", 1)[-1], "url": "/files/" + path.rsplit("/", 1)[-1]}
			for path in archive.namelist()
			if path.startswith("assets/") and not path.endswith("/")
		]
	mapping = {}
	for item in manifest:
		if not isinstance(item, dict) or not item.get("file", "").startswith("assets/"):
			frappe.throw("Invalid asset manifest.")
		doc = _insert(
			"File",
			{
				"file_name": item["file_name"],
				"is_private": int(bool(item.get("is_private"))),
				"content": archive.read(item["file"]),
			},
		)
		mapping[item["url"]] = doc.file_url
	return mapping


def _asset_urls(value, mapping):
	if isinstance(value, dict):
		return {key: _asset_urls(item, mapping) for key, item in value.items()}
	if isinstance(value, list):
		return [_asset_urls(item, mapping) for item in value]
	if isinstance(value, str):
		for old, new in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
			value = value.replace(old, new)
	return value


def import_bundle(zip_file_path):
	from lms.lms import course_import_export as legacy

	path = frappe.get_site_path(zip_file_path.lstrip("/"))
	legacy.validate_zip_file(path)
	try:
		with zipfile.ZipFile(path) as archive:
			course, chapters, lessons, assessments, entries = _validate(archive)
			mapping = _import_programs(archive, assessments, entries)
			# Only after every programming exercise has passed publication do we create
			# text, people, chapters, and their references.
			assets = _import_assets(archive)
			course, lessons = _asset_urls(course, assets), _asset_urls(lessons, assets)
			legacy.create_user_for_instructors(archive)
			legacy.create_evaluator(archive)
			_import_assessments(archive, assessments, mapping)
			structure = course.get("chapters", [])
			course_doc = legacy.create_course_doc(dict(course))
			chapter_map, lesson_map = {}, {}
			for name, data in chapters.items():
				chapter_map[name] = _insert(
					"Course Chapter", {**data, "lessons": [], "course": course_doc.name}
				)
			for name, data in lessons.items():
				values = {**data, "course": course_doc.name, "chapter": chapter_map[data["chapter"]].name}
				for field in ("content", "instructor_content"):
					values[field] = _replace_references(data.get(field), mapping)
				lesson_map[name] = _insert("Course Lesson", values).name
			for name, chapter in chapter_map.items():
				chapter.set(
					"lessons",
					[{"lesson": lesson_map[row["lesson"]]} for row in chapters[name].get("lessons", [])],
				)
				chapter.save(ignore_permissions=True)
			course_doc.reload()
			course_doc.set("chapters", [{"chapter": chapter_map[row["chapter"]].name} for row in structure])
			course_doc.save(ignore_permissions=True)
			return course_doc.name
	except Exception:
		# Full request rollback also executes File.on_rollback and discards deferred
		# jobs. A SQL savepoint alone would leave uploaded package files behind.
		frappe.db.rollback()
		raise
