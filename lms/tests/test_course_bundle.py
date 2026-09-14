import hashlib
import io
import json
import os
import unittest
import uuid
import zipfile
from unittest.mock import patch

import frappe

from lms.lms import course_bundle as bundle
from lms.lms import course_import_export as transfer


class TestCourseBundle(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.prefix = "bundle-test-" + uuid.uuid4().hex[:10]
		self.paths = []

	def tearDown(self):
		frappe.db.rollback()
		for path in self.paths:
			if os.path.isfile(path):
				os.remove(path)

	def doc(self, dt, **values):
		return frappe.get_doc({"doctype": dt, **values}).insert(ignore_permissions=True)

	def exercise(self, answer="3"):
		return self.doc(
			"LMS Programming Exercise",
			title=self.prefix,
			language="C++",
			problem_statement="<p>Sum</p>",
			test_cases=[{"input": "1 2", "expected_output": answer}],
		)

	def course(self, exercises):
		course = self.doc(
			"LMS Course",
			title=self.prefix,
			short_introduction="Bundle test",
			description="Text",
			is_public=0,
			instructors=[{"instructor": "Administrator"}],
		)
		chapter_names = []
		for exercise in exercises:
			chapter = self.doc("Course Chapter", title="同名章节", course=course.name)
			content = (
				{"blocks": [{"type": "program", "data": {"exercise": exercise.name}}]}
				if exercise
				else {"blocks": [{"type": "paragraph", "data": {"text": "正文"}}]}
			)
			lesson = self.doc(
				"Course Lesson",
				title="同名课时",
				course=course.name,
				chapter=chapter.name,
				content=json.dumps(content),
			)
			chapter.append("lessons", {"lesson": lesson.name})
			chapter.save(ignore_permissions=True)
			chapter_names.append(chapter.name)
		course.reload()
		for name in chapter_names:
			course.append("chapters", {"chapter": name})
		course.save(ignore_permissions=True)
		return course

	def export(self, course):
		out = io.BytesIO()
		lessons = transfer.get_lessons_for_export(course.name)
		assessments, questions, cases = transfer.get_course_assessments(lessons)
		transfer.build_course_zip(
			out,
			course,
			transfer.get_chapters_for_export(course.chapters),
			lessons,
			[],
			assessments,
			questions,
			cases,
			[],
			[],
		)
		return out.getvalue()

	def import_zip(self, content):
		name = self.prefix + "-" + uuid.uuid4().hex + ".zip"
		path = frappe.get_site_path("private", "files", name)
		self.paths.append(path)
		with open(path, "wb") as file:
			file.write(content)
		return frappe.get_doc("LMS Course", transfer.import_course_zip("/private/files/" + name))

	def lessons(self, course):
		return [
			frappe.get_doc("Course Lesson", row.lesson)
			for chapter in course.chapters
			for row in frappe.get_doc("Course Chapter", chapter.chapter).lessons
		]

	def refs(self, course):
		return [
			json.loads(lesson.content)["blocks"][0]["data"]["exercise"]
			for lesson in self.lessons(course)
			if lesson.lesson_type == "Programming"
		]

	def test_mixed_course_preserves_types_identity_and_repeated_references(self):
		first, second = self.exercise("3"), self.exercise("4")
		course = self.course([None, first, second, first])
		# Simulate an old record labelled Text before the lesson-type invariant existed.
		frappe.db.set_value("Course Lesson", self.lessons(course)[1].name, "lesson_type", "Text")
		content = self.export(course)
		with zipfile.ZipFile(io.BytesIO(content)) as archive:
			self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
			self.assertEqual(json.loads(archive.read("manifest.json"))["version"], 2)
		result = self.import_zip(content)
		self.assertEqual(result.is_public, 0)
		self.assertEqual(
			[lesson.lesson_type for lesson in self.lessons(result)],
			["Text", "Programming", "Programming", "Programming"],
		)
		self.assertEqual(len({lesson.name for lesson in self.lessons(result)}), 4)
		refs = self.refs(result)
		self.assertEqual(refs[0], refs[2])
		self.assertNotEqual(refs[0], refs[1])
		self.assertEqual(
			[frappe.get_doc("LMS Programming Exercise", name).test_cases[0].expected_output for name in refs],
			["3", "4", "3"],
		)

	def test_all_programs_import_before_course_and_failure_rolls_back(self):
		before = {dt: frappe.db.count(dt) for dt in ("LMS Course", "LMS Programming Exercise", "File")}
		content = self.export(self.course([self.exercise(), self.exercise()]))
		created = []
		original = bundle._insert

		def fail_second(dt, data):
			if dt == "LMS Programming Exercise" and created:
				raise RuntimeError("second problem failed")
			doc = original(dt, data)
			created.append(doc.name)
			return doc

		with (
			patch.object(bundle, "_insert", side_effect=fail_second),
			patch.object(transfer, "create_course_doc") as create_course,
		):
			with self.assertRaisesRegex(RuntimeError, "second problem"):
				self.import_zip(content)
			create_course.assert_not_called()
		for dt, count in before.items():
			self.assertEqual(frappe.db.count(dt), count)

	def test_missing_program_rejected(self):
		course = self.course([self.exercise()])
		content = self.export(course)
		out = io.BytesIO()
		with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(out, "w") as target:
			for name in source.namelist():
				if not name.startswith("assessments/"):
					target.writestr(name, source.read(name))
		with self.assertRaises(frappe.ValidationError):
			self.import_zip(out.getvalue())

	def icpc_content(self):
		out = io.BytesIO()
		with zipfile.ZipFile(out, "w") as archive:
			for name, content in {
				"problem.yaml": "name: " + self.prefix + "\nvalidation: default\nlicense: unknown\n",
				"problem_statement/problem.en.tex": r"\problemname{Sum} Print the sum.",
				"data/sample/01.in": "1 2\n",
				"data/sample/01.ans": "3\n",
				"data/secret/01.in": "2 3\n",
				"data/secret/01.ans": "5\n",
				"submissions/accepted/main.py": "a,b=map(int,input().split()); print(a+b)\n",
				"input_validators/main.py": "import sys\nsys.exit(42)\n",
			}.items():
				archive.writestr("problem/" + name, content)
		return out.getvalue()

	def icpc(self):
		from frappe.utils import add_days, now_datetime

		from lms.lms.problem_package import api

		content = self.icpc_content()
		file = self.doc("File", file_name=self.prefix + ".zip", is_private=1, content=content)
		record = frappe.get_doc(
			{
				"doctype": api.IMPORT,
				"file_id": file.name,
				"status": "Queued",
				"sha256": hashlib.sha256(content).hexdigest(),
				"expires_at": add_days(now_datetime(), 7),
			}
		)
		api._save(record)
		api.inspect_import(record.name)
		version = api.commit_import(
			record.name,
			options={
				"language": "C++",
				"time_limit_seconds": 2,
				"memory_limit_kb": 128000,
				"statement_path": "problem_statement/problem.en.tex",
			},
		)
		published = api.publish_version(version["version"])
		return frappe.get_doc(api.EXERCISE, published["exercise"])

	def test_icpc_roundtrip_retains_package_and_publication(self):
		with patch.object(bundle.packages, "_enabled"), patch.object(bundle.packages, "require_capability"):
			exercise = self.icpc()
			content = self.export(self.course([None, exercise, exercise]))
			with zipfile.ZipFile(io.BytesIO(content)) as archive:
				entry = json.loads(archive.read("manifest.json"))["programming_exercises"][0]
				self.assertEqual(hashlib.sha256(archive.read(entry["file"])).hexdigest(), entry["sha256"])
			result = self.import_zip(content)
			refs = self.refs(result)
			self.assertEqual(refs[0], refs[1])
			imported = frappe.get_doc(bundle.packages.EXERCISE, refs[0])
			self.assertEqual(imported.source_type, "icpc")
			version = frappe.get_doc(bundle.packages.VERSION, imported.active_package_version)
			self.assertEqual(version.status, "Published")
			self.assertEqual(len(json.loads(version.cases)), 2)
			self.assertEqual(json.loads(version.judge_config)["time_limit_seconds"], 2)

	def test_course_failure_removes_published_icpc_and_uploaded_files(self):
		doctypes = [
			bundle.packages.EXERCISE,
			bundle.packages.IMPORT,
			bundle.packages.VERSION,
			"File",
			"LMS Course",
		]
		before = {dt: frappe.db.count(dt) for dt in doctypes}
		paths = []
		original = bundle._insert

		def track_file(dt, data):
			doc = original(dt, data)
			if dt == "File":
				paths.append(doc.get_full_path())
			return doc

		with patch.object(bundle.packages, "_enabled"), patch.object(bundle.packages, "require_capability"):
			content = self.export(self.course([self.icpc()]))
			with (
				patch.object(bundle, "_insert", side_effect=track_file),
				patch.object(transfer, "create_course_doc", side_effect=RuntimeError("text import failed")),
			):
				with self.assertRaisesRegex(RuntimeError, "text import failed"):
					self.import_zip(content)
		for dt, count in before.items():
			self.assertEqual(frappe.db.count(dt), count)
		self.assertTrue(paths)
		self.assertTrue(all(not os.path.exists(path) for path in paths))

	def test_second_icpc_failure_removes_first_and_never_creates_course(self):
		doctypes = [
			bundle.packages.EXERCISE,
			bundle.packages.IMPORT,
			bundle.packages.VERSION,
			"File",
			"LMS Course",
		]
		before = {dt: frappe.db.count(dt) for dt in doctypes}
		with patch.object(bundle.packages, "_enabled"), patch.object(bundle.packages, "require_capability"):
			first = self.icpc()
			self.prefix += "-second"
			second = self.icpc()
			content = self.export(self.course([first, second]))
			published = []
			publish = bundle.packages.publish_version

			def fail_second(version):
				if published:
					raise RuntimeError("second ICPC rejected")
				result = publish(version)
				published.append(result["exercise"])
				return result

			with (
				patch.object(bundle.packages, "publish_version", side_effect=fail_second),
				patch.object(transfer, "create_course_doc") as create_course,
			):
				with self.assertRaisesRegex(RuntimeError, "second ICPC rejected"):
					self.import_zip(content)
				create_course.assert_not_called()
			self.assertEqual(len(published), 1)
		for dt, count in before.items():
			self.assertEqual(frappe.db.count(dt), count)

	def test_legacy_text_bundle_remains_importable(self):
		content = self.export(self.course([None]))
		out = io.BytesIO()
		with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(out, "w") as target:
			for name in source.namelist():
				if name not in ("manifest.json", "assets.json"):
					target.writestr(name, source.read(name))
		result = self.import_zip(out.getvalue())
		self.assertEqual(self.lessons(result)[0].lesson_type, "Text")

	def test_private_assets_keep_privacy_and_references(self):
		file = self.doc("File", file_name=self.prefix + ".txt", is_private=1, content=b"lesson asset")
		course = self.course([None])
		lesson = self.lessons(course)[0]
		lesson.content = json.dumps(
			{"blocks": [{"type": "upload", "data": {"file_url": file.file_url, "file_type": "text/plain"}}]}
		)
		lesson.save(ignore_permissions=True)
		out = io.BytesIO()
		lessons = transfer.get_lessons_for_export(course.name)
		transfer.build_course_zip(
			out,
			course,
			transfer.get_chapters_for_export(course.chapters),
			lessons,
			[file.file_url],
			[],
			[],
			[],
			[],
			[],
		)
		result = self.import_zip(out.getvalue())
		url = json.loads(self.lessons(result)[0].content)["blocks"][0]["data"]["file_url"]
		asset = frappe.get_doc("File", {"file_url": url})
		self.assertTrue(asset.is_private)
		self.assertEqual(asset.get_content(), "lesson asset")


class TestCourseAssetDiscovery(unittest.TestCase):
	def test_collects_images_nested_files_html_and_teacher_notes(self):
		lesson = frappe._dict(
			content=json.dumps({"blocks": [
				{"type": "image", "data": {"url": "http://school.localhost:8000/files/one.png"}},
				{"type": "image", "data": {"file": {"url": "/files/two.png"}}},
				{"type": "paragraph", "data": {"text": '<img src="/files/three.png">'}},
			]}),
			instructor_content=json.dumps({"blocks": [
				{"type": "upload", "data": {"file_url": "/private/files/notes.pdf"}},
			]}),
		)
		with patch.object(frappe.utils, "get_url", return_value="http://school.localhost:8000"):
			assets = transfer.get_course_assets(
				frappe._dict(image="/files/one.png"), [lesson], [], [],
				[{"question": '<img src="/files/question.png">'}],
			)
		self.assertEqual(set(assets), {
			"/files/one.png", "/files/two.png", "/files/three.png",
			"/private/files/notes.pdf", "/files/question.png",
		})
		self.assertEqual(len(assets), 5)

	def test_portable_json_keeps_external_urls_and_preserves_source(self):
		local = "http://school.localhost:8000/files/image.png"
		external = "https://example.org/files/external.png"
		data = {"content": json.dumps({"blocks": [{"data": {"url": local}}]}), "external": external}
		with patch.object(frappe.utils, "get_url", return_value="http://school.localhost:8000"):
			result = json.loads(transfer.frappe_json_dumps(data))
			self.assertEqual(list(transfer.asset_references(external)), [])
		self.assertEqual(json.loads(result["content"])["blocks"][0]["data"]["url"], "/files/image.png")
		self.assertEqual(result["external"], external)
		self.assertIn(local, data["content"])


	def test_code_resembling_malformed_url_is_preserved(self):
		code = "answer = value //array[index]"
		self.assertIsNone(transfer.local_asset_url("//array[index]"))
		self.assertEqual(list(transfer.asset_references(code)), [])
		self.assertEqual(transfer.portable_asset_urls(code), code)
		self.assertEqual(transfer.local_asset_url("/files/valid.png"), "/files/valid.png")
