import os
import tempfile
import time
import unittest
from unittest.mock import patch

import frappe
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from lms.lms import course_export_jobs as jobs
from lms.lms import course_import_export as transfer


class TestCourseExportJobs(unittest.TestCase):
	def test_cleanup_retains_new_archives_and_removes_only_expired_exports(self):
		with tempfile.TemporaryDirectory() as directory:
			for name in ("new.zip", "old.zip", "old.partial", "unrelated.txt"):
				path = os.path.join(directory, name)
				with open(path, "wb") as stream:
					stream.write(b"zip")
				if name != "new.zip":
					os.utime(path, (0, 0))
			with patch.object(jobs, "export_directory", return_value=directory):
				jobs.cleanup_exports()
			self.assertEqual(set(os.listdir(directory)), {"new.zip", "unrelated.txt"})

	def test_download_stream_supports_range(self):
		with tempfile.NamedTemporaryFile() as file:
			file.write(b"0123456789")
			file.flush()
			request = Request(EnvironBuilder(headers={"Range": "bytes=3-6"}).get_environ())
			with patch.object(frappe.local, "request", request, create=True):
				response = transfer.serve_zip(file.name, "course.zip")
				self.assertEqual(response.status_code, 206)
				self.assertEqual(response.headers["Content-Range"], "bytes 3-6/10")
				self.assertEqual(b"".join(response.response), b"3456")
				response.close()

	def test_export_failure_removes_partial_archive(self):
		with tempfile.TemporaryDirectory() as directory:
			def fail(path, *args, **kwargs):
				with open(path, "wb") as stream:
					stream.write(b"partial")
				raise RuntimeError("disk full")
			with patch.object(jobs, "export_directory", return_value=directory), patch.object(transfer, "build_course_zip", side_effect=fail):
				with self.assertRaises(frappe.ValidationError):
					transfer.create_course_zip("test.zip", None, [], [], [], [], [], [], [], [], download=False)
			self.assertEqual(os.listdir(directory), [])

	def test_status_rejects_other_user(self):
		with patch.object(frappe.cache, "get_value", return_value={"owner": "someone-else"}):
			with self.assertRaises(frappe.PermissionError):
				jobs.export_status("token")

	def test_failed_worker_is_visible_to_client(self):
		state = dict(owner=frappe.session.user, course="l4", status="queued", created=time.time())
		with patch.object(frappe.cache, "get_value", return_value=state), patch.object(jobs, "_authorize"), patch.object(jobs, "_save") as save, patch.object(transfer, "export_course_zip", side_effect=RuntimeError("missing asset")), patch.object(frappe, "log_error"):
			jobs.prepare_export("token")
			self.assertEqual(save.call_args.args[1]["status"], "failed")

	def test_timeout_is_reported_instead_of_polling_forever(self):
		state = dict(status="running", created=time.time() - jobs.JOB_TIMEOUT - 1)
		with patch.object(jobs, "_state", return_value=state):
			self.assertEqual(jobs.export_status("token")["status"], "failed")

	def test_revoked_course_permission_blocks_status_and_download(self):
		state = dict(owner=frappe.session.user, course="l4", status="ready", path="unused")
		with patch.object(frappe.cache, "get_value", return_value=state), patch.object(jobs, "_authorize", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				jobs.export_status("token")
			with self.assertRaises(frappe.PermissionError):
				jobs.download_export("token")

	def test_worker_builds_archive_without_http_response(self):
		state = dict(owner=frappe.session.user, course="l5", status="queued", created=time.time())
		with patch.object(frappe.cache, "get_value", return_value=state), patch.object(jobs, "_authorize"), patch.object(jobs, "_save") as save, patch.object(transfer, "export_course_zip", return_value="/private/course-exports/test.zip") as export:
			jobs.prepare_export("token")
			export.assert_called_once_with("l5", download=False, include_videos=True)
			self.assertEqual(save.call_args.args[1]["status"], "ready")

	def test_out_of_bounds_range_returns_416(self):
		from werkzeug.exceptions import RequestedRangeNotSatisfiable

		with tempfile.NamedTemporaryFile() as file:
			file.write(b"zip")
			file.flush()
			request = Request(EnvironBuilder(headers={"Range": "bytes=99-"}).get_environ())
			with patch.object(frappe.local, "request", request, create=True):
				with self.assertRaises(RequestedRangeNotSatisfiable):
					transfer.serve_zip(file.name, "course.zip")

	def test_worker_preserves_video_choice(self):
		state = dict(owner=frappe.session.user, course="l5", status="queued", created=time.time(), include_videos=False)
		with patch.object(frappe.cache, "get_value", return_value=state), patch.object(jobs, "_authorize"), patch.object(jobs, "_save"), patch.object(transfer, "export_course_zip", return_value="test.zip") as export:
			jobs.prepare_export("token")
			export.assert_called_once_with("l5", download=False, include_videos=False)

	def test_active_jobs_are_reused_only_for_same_video_choice(self):
		from contextlib import nullcontext

		cache = {}
		with patch.object(jobs, "_authorize"), patch.object(frappe.cache, "lock", side_effect=lambda *a, **kw: nullcontext()), patch.object(frappe.cache, "get_value", side_effect=cache.get), patch.object(frappe.cache, "set_value", side_effect=lambda key, value, **kw: cache.update({key: value})), patch.object(frappe, "enqueue") as enqueue:
			with_video = jobs.start_export("course", "1")
			without_video = jobs.start_export("course", "0")
			self.assertNotEqual(with_video, without_video)
			self.assertEqual(jobs.start_export("course", False), without_video)
			self.assertEqual(jobs.start_export("course"), with_video)
			self.assertEqual(enqueue.call_count, 2)

	def test_start_export_passes_enforced_http_type_validation(self):
		import inspect
		from frappe.utils.typing_validations import transform_parameter_types

		# HTTP requests enforce annotations; ordinary direct calls skip this layer.
		method = inspect.unwrap(jobs.start_export)
		for value, expected in (("0", False), ("1", True), (False, False), (True, True)):
			with self.subTest(value=value):
				args, kwargs = transform_parameter_types(
					method, (), {"course_name": "course", "include_videos": value}, force_types=True
				)
				self.assertEqual(args, [])
				self.assertEqual(bool(kwargs["include_videos"]), expected)
		transform_parameter_types(method, (), {"course_name": "course"}, force_types=True)
