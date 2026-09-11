"""Bulk export contracts, runnable with bench's Python via unittest."""

import hashlib
import io
import json
import zipfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from lms.lms.problem_package import export


def fixture_package(flat=False):
	out = io.BytesIO()
	files = {
		"problem.yaml": b"name: Example\nproblem_format_version: legacy-icpc\n",
		"problem_statement/problem.en.pdf": b"%PDF-1.4\n",
		"data/secret/01.in": b"1\n",
		"data/secret/01.ans": b"",
		"data/sample/01.in": b"2\n",
		"data/sample/01.ans": b"2\n",
		"submissions/accepted/main.py": b"#!/usr/bin/env python3\nprint(1)\n",
		"input_validators/check/run": b"#!/bin/sh\nexit 42\n",
	}
	with zipfile.ZipFile(out, "w") as archive:
		for path, content in files.items():
			info = zipfile.ZipInfo(("" if flat else "example/") + path)
			info.external_attr = 0o100755 << 16
			archive.writestr(info, content)
	return out.getvalue(), files


class TestPackageExport(TestCase):
	def test_normalizes_flat_and_rooted_archives_without_losing_data_or_modes(self):
		for flat in (True, False):
			content, files = fixture_package(flat)
			package, report = export.package_zip(content, "p001", allow_flat=flat)
			self.assertEqual(report["errors"], [])
			with zipfile.ZipFile(io.BytesIO(package)) as archive:
				self.assertEqual(set(archive.namelist()), {"p001/" + p for p in files})
				for path, data in files.items():
					self.assertEqual(archive.read("p001/" + path), data)
				self.assertEqual(
					archive.getinfo("p001/input_validators/check/run").external_attr >> 16, 0o100755
				)

	def test_rejects_incomplete_and_unsafe_packages(self):
		for path in ("example/problem.yaml", "../problem.yaml"):
			out = io.BytesIO()
			with zipfile.ZipFile(out, "w") as archive:
				archive.writestr(path, "name: Missing\n")
			with self.assertRaises(export.PackageError):
				export.package_zip(out.getvalue(), "p001")

	def setUp(self):
		self.response = SimpleNamespace()
		self.frappe = Mock()
		self.frappe.session.user = "teacher"
		self.frappe.local.response = self.response
		self.frappe.local.response_headers = {}
		self.frappe.PermissionError = PermissionError
		self.frappe.parse_json = json.loads
		self.frappe.throw.side_effect = ValueError
		self.exercise = SimpleNamespace(
			name="EX1",
			title="同名题目",
			source_type="icpc",
			active_package_version="V1",
			check_permission=Mock(),
		)
		self.version = SimpleNamespace(
			name="V1",
			exercise="EX1",
			status="Published",
			import_record="I1",
			judge_config='{"time_limit_seconds":2}',
			check_permission=Mock(),
		)
		self.record = SimpleNamespace(allow_flat=False, check_permission=Mock())
		self.frappe.get_doc.side_effect = lambda doctype, name: {
			export.EXERCISE: self.exercise,
			export.VERSION: self.version,
			export.IMPORT: self.record,
		}[doctype]
		self.patchers = [patch.object(export, "frappe", self.frappe), patch.object(export, "_", lambda s: s)]
		for patcher in self.patchers:
			patcher.start()
			self.addCleanup(patcher.stop)

	@patch.object(export, "_content")
	def test_download_is_zip_with_independent_package_and_manifest(self, content):
		content.return_value = fixture_package()[0]
		export.export_exercises('["EX1", "EX1"]')
		self.assertEqual(self.response.content_type, "application/zip")
		self.assertEqual(self.frappe.local.response_headers["Cache-Control"], "private, no-store")
		self.exercise.check_permission.assert_any_call("write")
		self.exercise.check_permission.assert_any_call("export")
		with zipfile.ZipFile(io.BytesIO(self.response.filecontent)) as bundle:
			manifest = json.loads(bundle.read("manifest.json"))
			self.assertEqual(len(manifest), 1)
			self.assertEqual(manifest[0]["title"], "同名题目")
			package = bundle.read(manifest[0]["file"])
			self.assertEqual(manifest[0]["sha256"], hashlib.sha256(package).hexdigest())
			self.assertEqual(export.preflight(package)["errors"], [])

	@patch.object(export, "_content")
	def test_all_permissions_checked_before_reading_any_package(self, content):
		denied = SimpleNamespace(check_permission=Mock(side_effect=PermissionError))
		self.frappe.get_doc.side_effect = [self.exercise, denied]
		with self.assertRaises(PermissionError):
			export.export_exercises(["EX1", "EX2"])
		content.assert_not_called()
		self.assertFalse(hasattr(self.response, "filecontent"))

	@patch.object(export, "_content")
	def test_guest_and_student_cannot_download_secrets(self, content):
		self.frappe.session.user = "Guest"
		with self.assertRaises(PermissionError):
			export.export_exercises(["EX1"])
		self.frappe.session.user = "student"
		self.exercise.check_permission.side_effect = lambda kind: (
			(_ for _ in ()).throw(PermissionError()) if kind == "write" else None
		)
		with self.assertRaises(PermissionError):
			export.export_exercises(["EX1"])
		content.assert_not_called()

	@patch.object(export, "_content")
	def test_incomplete_exercise_and_version_mismatch_fail_without_partial_download(self, content):
		self.exercise.source_type = "manual"
		with self.assertRaises(ValueError):
			export.export_exercises(["EX1"])
		self.exercise.source_type = "icpc"
		self.version.exercise = "another-exercise"
		with self.assertRaises(ValueError):
			export.export_exercises(["EX1"])
		content.assert_not_called()
		self.assertFalse(hasattr(self.response, "filecontent"))

	def test_selection_validation(self):
		for selection in ([], ["EX1"] * 51, "oops", {}, [1], [""], ["a" * 141]):
			with self.subTest(selection=selection), self.assertRaises(ValueError):
				export.export_exercises(selection)
		self.frappe.get_doc.assert_not_called()

	@patch.object(export, "MAX_TOTAL_BYTES", 5)
	@patch.object(export, "_content")
	def test_batch_capacity_is_bounded(self, content):
		content.return_value = fixture_package()[0]
		with self.assertRaises(ValueError):
			export.export_exercises(["EX1"])
		self.assertFalse(hasattr(self.response, "filecontent"))

	@patch.object(export, "_content")
	def test_tex_preferred_and_macos_metadata_omitted(self, content):
		original, files = fixture_package()
		out = io.BytesIO(original)
		tex = b"\\section{Example} $a+b$"
		with zipfile.ZipFile(out, "a") as archive:
			archive.writestr("example/problem_statement/problem.en.tex", tex)
			archive.writestr("__MACOSX/._example", b"metadata")
			archive.writestr("example/.DS_Store", b"metadata")
		content.return_value = out.getvalue()
		export.export_exercises(["EX1"])
		with zipfile.ZipFile(io.BytesIO(self.response.filecontent)) as bundle:
			manifest = json.loads(bundle.read("manifest.json"))[0]
			self.assertEqual(manifest["statement_path"], "problem_statement/problem.en.tex")
			with zipfile.ZipFile(io.BytesIO(bundle.read(manifest["file"]))) as package:
				self.assertFalse(any(export.is_macos_metadata(p) for p in package.namelist()))
				self.assertEqual(package.read(manifest["file"][:-4] + "/problem_statement/problem.en.tex"), tex)
