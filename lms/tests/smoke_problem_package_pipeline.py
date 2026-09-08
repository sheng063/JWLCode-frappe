"""Explicit live smoke test, run in an initialized Frappe site against a temporary judge service.

The caller supplies an internal URL. All fixture database writes are rolled back.
"""

import os
import time
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import frappe
import requests

from lms.lms import judge_service as judge
from lms.lms.problem_package import api
from lms.tests.test_problem_package_integration import package


def run(service_url):
	original_settings = judge._get_settings()
	settings = SimpleNamespace(
		service_url=service_url,
		get_password=original_settings.get_password,
		request_timeout_seconds=10,
		callback_url="http://127.0.0.1:9/icpc-smoke-callback",
	)
	response = requests.get(
		service_url + "/internal/v1/capabilities",
		headers={"Authorization": "Bearer " + settings.get_password("api_token")},
		timeout=10,
	)
	response.raise_for_status()
	memory = max(131072, response.json()["min_memory_limit_kb"])
	paths = []
	previous_enabled = frappe.conf.get("enable_icpc_problem_packages")
	frappe.conf.enable_icpc_problem_packages = 1
	frappe.set_user("Administrator")

	def import_version(answer, target=None, current=""):
		file = frappe.get_doc(
			dict(doctype="File", file_name=f"smoke-{uuid4().hex}.zip", is_private=1, content=package(answer))
		).insert()
		paths.append(file.get_full_path())
		created = api.create_import(file.name, target)
		api.inspect_import(created["name"])
		assert api.get_import(created["name"])["status"] == "Ready"
		version = api.commit_import(
			created["name"],
			current,
			dict(
				language="Python",
				statement_path="problem_statement/problem.en.pdf",
				time_limit_seconds=2,
				memory_limit_kb=memory,
			),
		)["version"]
		return version, api.publish_version(version)["exercise"]

	try:
		with patch.object(frappe, "enqueue"), patch.object(judge, "_get_settings", return_value=settings):
			v1, exercise = import_version(b"YES\n")
			created = judge.submit_programming_exercise(exercise, "print('yes')", uuid4().hex)
			v2, _ = import_version(b"NO\n", exercise, v1)
			# Dispatch only after switching the active pointer: it must still execute v1.
			judge.dispatch_submission(created["submission"])
			for _ in range(120):
				status = judge.get_programming_submission_status(created["submission"])
				if status["status"] not in {"Queued", "Running", "Compiling"}:
					break
				time.sleep(1)
			else:
				raise TimeoutError("Submission did not finish")
			doc = frappe.get_doc("LMS Programming Exercise Submission", created["submission"])
			assert status["status"] == "Passed" and doc.score == 100, status
			assert doc.package_version == v1 and not doc.compiler_message and not doc.test_cases
			assert frappe.db.get_value(api.EXERCISE, exercise, "active_package_version") == v2
			print(
				"PASS: upload -> preflight -> publish -> submit -> switch version -> Judge0 -> poll -> AC/100; hidden data absent",
				flush=True,
			)
	finally:
		frappe.db.rollback()
		frappe.conf.enable_icpc_problem_packages = previous_enabled
		for path in paths:
			if os.path.exists(path):
				os.remove(path)
