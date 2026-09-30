"""Run with unittest; pure archive tests and rollback-only site integration tests."""
import io
import json
import zipfile
from unittest import TestCase
from unittest.mock import patch

import frappe
from lms.lms.problem_package import api, editor
from lms.lms.problem_package.parser import PackageError, preflight, read_archive
from lms.tests.test_problem_package_integration import TestProblemPackageIntegration, package


class TestEditorArchives(TestCase):
	def test_hidden_roundtrip_preserves_empty_and_unicode(self):
		cases = [{"input": "", "expected_output": ""}, {"input": "中文\n\n", "expected_output": "42\n"}]
		self.assertEqual(editor.parse_hidden_zip(editor.hidden_zip(cases)), cases)

	def test_invalid_uploads_reject_before_replacement(self):
		for files in ({"../01.in": "x", "01.ans": "y"}, {"01.in": "x"}, {"01.ans": "y"}, {"x.py": "pass"}, {"01.in": "\x00", "01.ans": "y"}):
			out = io.BytesIO()
			with zipfile.ZipFile(out, "w") as archive:
				for path, value in files.items():
					archive.writestr(path, value)
			with self.assertRaises(PackageError):
				editor.parse_hidden_zip(out.getvalue())

	def test_rebuild_updates_tex_samples_and_secrets(self):
		source = r"\section{描述} $a_1 \leq b$"
		content = editor.rebuild_package(package(sample=True), "新题目", [{"input": "1", "expected_output": "2"}],
			[{"input": "3", "expected_output": "4"}], source)
		report = preflight(content)
		self.assertEqual(report["errors"], [])
		self.assertEqual(report["title"], "新题目")
		self.assertEqual([c["expected_output"] for c in report["cases"]], ["2\n", "4\n"])
		files = read_archive(content)
		self.assertEqual(files["fixture/problem_statement/problem.tex"].decode(), source)
		self.assertEqual(files["fixture/submissions/accepted/main.py"], b"print('yes')\n")
		self.assertNotIn("fixture/data/secret/01.in", files)


class TestEditorIntegration(TestProblemPackageIntegration):
	def setUp(self):
		super().setUp()
		self.existing_files = set(frappe.get_all("File", pluck="name"))

	def tearDown(self):
		for name in frappe.get_all("File", filters={"file_name": "edited-problem.zip"}, pluck="name"):
			if name not in self.existing_files:
				self.files.append(frappe.get_doc("File", name).get_full_path())
		super().tearDown()

	def test_edit_and_hidden_replace_preserve_identity_and_history(self):
		import_id, _ = self.imported(package(sample=True))
		v1 = self.confirm(import_id)
		published = api.publish_version(v1)
		doc = frappe.get_doc(api.EXERCISE, published["exercise"])
		old_modified = str(doc.modified)
		source = r"\section{描述} $a_1 \leq b$"
		editor.save_exercise(doc.name, old_modified, "Edited title", "", [{"input": "2", "expected_output": "3"}], source)
		doc.reload()
		self.assertEqual(doc.exercise_number, published["exercise_number"])
		self.assertNotEqual(doc.active_package_version, v1)
		self.assertIn(source, doc.problem_statement)
		self.assertEqual(doc.test_cases[0].expected_output, "3\n")
		self.assertEqual(json.loads(frappe.get_doc(api.VERSION, v1).cases)[0]["expected_output"], "yes\n")
		with self.assertRaises(frappe.ValidationError):
			editor.save_exercise(doc.name, old_modified, "Stale", "", [], source)
		file = frappe.get_doc({"doctype": "File", "file_name": "hidden-editor-test.zip", "is_private": 1,
			"content": editor.hidden_zip([{"input": "9\n", "expected_output": "10\n"}])}).insert()
		self.files.append(file.get_full_path())
		editor.upload_hidden_cases(doc.name, str(doc.modified), file.name)
		doc.reload()
		self.assertEqual(doc.exercise_number, published["exercise_number"])
		self.assertEqual(editor._cases(doc)[0]["expected_output"], "10\n")
		self.assertEqual(len(editor._cases(doc)), 1)
		self.assertIn(source, doc.problem_statement)
		# A full replacement uses the same target and retains both identifiers.
		i2, _ = self.imported(package(b"replacement\n"), doc.name)
		v2 = self.confirm(i2, doc.active_package_version)
		replacement = api.publish_version(v2)
		self.assertEqual(replacement["exercise"], doc.name)
		self.assertEqual(replacement["exercise_number"], published["exercise_number"])

	def test_limits_can_be_edited_independently_and_preserve_history(self):
		import_id, _ = self.imported(package(sample=True))
		v1 = self.confirm(import_id)
		doc = frappe.get_doc(api.EXERCISE, api.publish_version(v1)["exercise"])
		samples = [{"input": c.input, "expected_output": c.expected_output} for c in doc.test_cases]
		editor.save_exercise(doc.name, str(doc.modified), doc.title, doc.problem_statement, samples,
			time_limit_seconds=1.5)
		doc.reload()
		self.assertEqual(doc.time_limit_seconds, 1.5)
		self.assertEqual(doc.memory_limit_kb, 131072)
		editor.save_exercise(doc.name, str(doc.modified), doc.title, doc.problem_statement, samples,
			memory_limit_kb=262144)
		doc.reload()
		config = json.loads(frappe.get_doc(api.VERSION, doc.active_package_version).judge_config)
		self.assertEqual(config["time_limit_seconds"], 1.5)
		self.assertEqual(config["memory_limit_kb"], 262144)
		self.assertEqual(doc.memory_limit_kb, 262144)
		self.assertEqual(json.loads(frappe.get_doc(api.VERSION, v1).judge_config)["memory_limit_kb"], 131072)
		version = frappe.get_doc(api.VERSION, doc.active_package_version)
		report = preflight(api._content(frappe.get_doc(api.IMPORT, version.import_record)))
		self.assertEqual(report["metadata"]["limits"]["memory"], 256)

	def test_manual_limits_and_invalid_values(self):
		samples = [{"input": "", "expected_output": "yes"}]
		doc = frappe.get_doc({"doctype": api.EXERCISE, "title": "Limits fixture", "language": "Python",
			"problem_statement": "Test", "test_cases": samples}).insert()
		editor.save_exercise(doc.name, str(doc.modified), doc.title, doc.problem_statement, samples,
			time_limit_seconds=2.5, memory_limit_kb=262144)
		doc.reload()
		self.assertEqual(doc.time_limit_seconds, 2.5)
		self.assertEqual(doc.memory_limit_kb, 262144)
		for limits in ({"time_limit_seconds": 0}, {"time_limit_seconds": 31},
			{"time_limit_seconds": float("nan")}, {"memory_limit_kb": 15999},
			{"memory_limit_kb": 1048577}, {"memory_limit_kb": 16000.5}):
			with self.subTest(limits=limits), self.assertRaises(frappe.ValidationError):
				editor.save_exercise(doc.name, str(doc.modified), doc.title, doc.problem_statement, samples, **limits)

	def test_pdf_description_survives_version_and_export(self):
		i1, _ = self.imported(package(sample=True))
		published = api.publish_version(self.confirm(i1))
		doc = frappe.get_doc(api.EXERCISE, published["exercise"])
		description = doc.problem_statement + '<p>Description $x^2$</p>'
		editor.save_exercise(doc.name, str(doc.modified), doc.title, description, [{"input": "", "expected_output": "yes\n"}])
		doc.reload()
		self.assertIn('Description $x^2$', doc.problem_statement)
		self.assertIn(doc.active_package_version, doc.problem_statement)
		self.assertNotIn(published["version"], doc.problem_statement)

	def test_student_cannot_read_or_replace_hidden_cases(self):
		with patch.object(api, "_manage", side_effect=frappe.PermissionError):
			for action in (lambda: editor.download_hidden_cases("E1"), lambda: editor.hidden_case_count("E1"), lambda: editor.preview_hidden_cases("E1"),
				lambda: editor.upload_hidden_cases("E1", "now", "F1")):
				with self.assertRaises(frappe.PermissionError):
					action()

	def test_manual_hidden_upload_is_full_replacement_and_invalid_zip_preserves_data(self):
		doc = frappe.get_doc({"doctype": api.EXERCISE, "title": "Manual editor fixture", "language": "Python",
			"problem_statement": "<p>$x$</p>", "test_cases": [{"input": "", "expected_output": "yes"}]}).insert()
		old = frappe.get_doc({"doctype": "LMS Judge Test Case", "exercise": doc.name, "hidden": 1,
			"input": "old", "expected_output": "old"}).insert()
		file = frappe.get_doc({"doctype": "File", "file_name": "manual-hidden-editor.zip", "is_private": 1,
			"content": editor.hidden_zip([{"input": "new", "expected_output": "new"}])}).insert()
		self.files.append(file.get_full_path())
		editor.upload_hidden_cases(doc.name, str(doc.modified), file.name)
		doc.reload()
		self.assertFalse(frappe.db.exists("LMS Judge Test Case", old.name))
		self.assertEqual(editor._cases(doc)[0]["input"], "new")
		with patch.object(editor, "parse_hidden_zip", side_effect=PackageError("Missing pair")):
			with self.assertRaises(PackageError):
				editor.upload_hidden_cases(doc.name, str(doc.modified), file.name)
		self.assertEqual(editor._cases(doc)[0]["input"], "new")
