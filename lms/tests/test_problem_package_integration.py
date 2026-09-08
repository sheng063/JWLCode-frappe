"""Run on a migrated local site; fixtures are rolled back and private files removed."""

import io
import json
import os
import zipfile
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

import frappe

from lms.lms.problem_package import api


def package(answer=b"yes\n", sample=False):
	stream = io.BytesIO()
	files = {
		"problem.yaml": b"name: Integration fixture\nproblem_format_version: legacy-icpc\n",
		"problem_statement/problem.en.pdf": b"%PDF-1.4\n%%EOF\n",
		"data/secret/01.in": b"",
		"data/secret/01.ans": answer,
		"input_validators/main.py": b"pass\n",
		"submissions/accepted/main.py": b"print('yes')\n",
	}
	if sample:
		files.update({"data/sample/01.in": b"", "data/sample/01.ans": answer})
	with zipfile.ZipFile(stream, "w") as archive:
		for path, value in files.items():
			archive.writestr("fixture/" + path, value)
	return stream.getvalue()


class TestProblemPackageIntegration(TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.enabled = frappe.conf.get("enable_icpc_problem_packages")
		frappe.conf.enable_icpc_problem_packages = 1
		self.files = []
		self.enqueue = patch.object(frappe, "enqueue").start()
		self.capability = patch.object(api, "require_capability").start()

	def tearDown(self):
		patch.stopall()
		frappe.set_user("Administrator")
		frappe.db.rollback()
		frappe.conf.enable_icpc_problem_packages = self.enabled
		for path in self.files:
			if os.path.exists(path):
				os.remove(path)

	def imported(self, content=None, target=None):
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"fixture-{uuid4().hex}.zip",
				"is_private": 1,
				"content": content if content is not None else package(),
			}
		).insert()
		self.files.append(file.get_full_path())
		created = api.create_import(file.name, target)
		api.inspect_import(created["name"])
		assert api.get_import(created["name"])["status"] == "Ready"
		return created["name"], file

	def confirm(self, import_id, expected=""):
		return api.commit_import(
			import_id,
			expected,
			dict(
				language="Python",
				statement_path="problem_statement/problem.en.pdf",
				time_limit_seconds=3,
				memory_limit_kb=131072,
			),
		)["version"]

	def test_empty_answer_no_samples_publish_and_idempotency(self):
		import_id, _ = self.imported(package(b""))
		version = self.confirm(import_id)
		assert self.confirm(import_id) == version
		assert not frappe.db.get_value(api.VERSION, version, "exercise")
		published = api.publish_version(version)
		assert api.publish_version(version) == published
		exercise = frappe.get_doc(api.EXERCISE, published["exercise"])
		assert exercise.active_package_version == version
		assert exercise.test_cases == [] and exercise.feedback_policy == "strict"
		assert json.loads(frappe.get_doc(api.VERSION, version).cases)[0]["expected_output"] == ""
		exercise.title = "Direct mutation"
		with self.assertRaises(frappe.ValidationError):
			exercise.save()

	def test_concurrent_target_version_does_not_overwrite(self):
		first, _ = self.imported()
		v1 = self.confirm(first)
		exercise = api.publish_version(v1)["exercise"]
		second, _ = self.imported(package(b"no\n"), exercise)
		third, _ = self.imported(package(b"different\n"), exercise)
		v2, v3 = self.confirm(second, v1), self.confirm(third, v1)
		api.publish_version(v2)
		with self.assertRaises(frappe.ValidationError):
			api.publish_version(v3)
		assert frappe.db.get_value(api.EXERCISE, exercise, "active_package_version") == v2

	def test_private_records_files_and_generic_writes(self):
		import_id, file = self.imported()
		version = self.confirm(import_id)
		student = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"icpc-{uuid4().hex}@example.invalid",
				"first_name": "ICPC Test",
				"send_welcome_email": 0,
				"roles": [{"role": "LMS Student"}],
			}
		).insert()
		assert not frappe.has_permission(api.IMPORT, "read", import_id, user=student.name)
		assert not frappe.has_permission(api.VERSION, "read", version, user=student.name)
		assert not frappe.has_permission("File", "read", file.name, user=student.name)
		file.is_private = 0
		with self.assertRaises(frappe.ValidationError):
			file.save()
		doc = frappe.get_doc(api.VERSION, version)
		doc.flags.package_service = True  # A client-serializable flag cannot bypass the controller.
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_submit_freezes_version_and_filters_result(self):
		from lms.lms.judge_service import _apply_result, submit_programming_exercise

		import_id, _ = self.imported()
		version = self.confirm(import_id)
		exercise = api.publish_version(version)["exercise"]
		created = submit_programming_exercise(exercise, "print('no')", uuid4().hex)
		doc = frappe.get_doc("LMS Programming Exercise Submission", created["submission"])
		assert doc.package_version == version
		frappe.db.set_value(doc.doctype, doc.name, "judge_request_id", "REQ-INTEGRATION")
		doc.reload()
		_apply_result(
			doc,
			dict(
				package_version=version,
				config_digest=doc.config_digest,
				attempt_id=doc.attempt_id,
				judge_request_id=doc.judge_request_id,
				status="WRONG_ANSWER",
				status_version=1,
				event_id="event1",
				score=50,
				compiler_message="SECRET",
				cases=[dict(case_id="data/secret/01", status="Wrong Answer", stdout="SECRET")],
			),
		)
		doc.reload()
		assert doc.score == 0 and not doc.compiler_message and not doc.test_cases

	def test_signed_callback_and_terminal_result_are_protected(self):
		import hashlib
		import hmac
		import time
		from types import SimpleNamespace

		from lms.lms import judge_service as judge

		import_id, _ = self.imported()
		version = self.confirm(import_id)
		exercise = api.publish_version(version)["exercise"]
		created = judge.submit_programming_exercise(exercise, "print('yes')", uuid4().hex)
		doc = frappe.get_doc("LMS Programming Exercise Submission", created["submission"])
		frappe.db.set_value(doc.doctype, doc.name, "judge_request_id", "REQ-CALLBACK")
		data = dict(
			submission_id=doc.name,
			package_version=version,
			config_digest=doc.config_digest,
			attempt_id=doc.attempt_id,
			judge_request_id="REQ-CALLBACK",
			status="ACCEPTED",
			status_version=1,
			event_id="event1",
			cases=[dict(case_id="data/secret/01", status="Accepted")],
		)
		body = json.dumps(data).encode()
		timestamp = str(int(time.time()))
		secret = "callback-test-secret"
		headers = {
			"X-JWL-Timestamp": timestamp,
			"X-JWL-Signature": "sha256="
			+ hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest(),
		}
		with (
			patch.object(
				judge, "_get_settings", return_value=SimpleNamespace(get_password=lambda key: secret)
			),
			patch.object(frappe, "get_request_header", side_effect=headers.get),
			patch.object(frappe, "request", SimpleNamespace(get_data=lambda: body), create=True),
		):
			assert judge.judge_callback()["terminal"]
			assert judge.judge_callback()["duplicate"]
			with self.assertRaises(frappe.AuthenticationError):
				judge._verify_callback(body + b" ")
		doc.reload()
		assert doc.status == "Passed" and doc.score == 100
		data.update(status="RUNNING", status_version=2, event_id="late-running")
		judge._apply_result(doc, data)
		doc.reload()
		assert doc.status == "Passed" and doc.score == 100
