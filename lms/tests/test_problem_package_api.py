"""Boundary tests; database transactions also require bench integration coverage."""

import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from lms.lms.problem_package import api
from lms.lms.problem_package.permissions import protect_file


class TestPackageAPI(TestCase):
	@patch.object(api, "_owned")
	def test_preview_summary_never_contains_secret_cases(self, owned):
		owned.return_value = SimpleNamespace(
			name="I1",
			status="Ready",
			package_version=None,
			report=json.dumps(
				{
					"cases": [
						dict(case_id="sample", input="public", hidden=False),
						dict(case_id="secret", input="SECRET", hidden=True),
					]
				}
			),
		)
		result = api.get_import("I1")
		assert result["hidden_count"] == 1
		assert "SECRET" not in json.dumps(result)

	@patch.object(api, "_manage")
	@patch.object(api.frappe, "get_roles", create=True, return_value=[])
	@patch.object(api.frappe, "get_doc")
	def test_other_owner_cannot_read_import(self, get_doc, roles, manage):
		get_doc.return_value = SimpleNamespace(owner="another", target_exercise=None)
		with self.assertRaises(Exception):
			api._owned("I1")
		manage.assert_not_called()

	@patch("lms.lms.judge_service._get_settings")
	@patch.object(api.requests, "get")
	def test_capability_cannot_silently_fall_back(self, get, settings):
		settings.return_value = SimpleNamespace(service_url="http://judge", get_password=lambda key: "token")
		get.return_value = SimpleNamespace(raise_for_status=Mock(), json=lambda: {"protocols": []})
		with self.assertRaises(Exception):
			api.require_capability()

	@patch.object(api.frappe, "db")
	def test_original_file_cannot_be_made_public_or_deleted(self, db):
		db.exists.return_value = True
		doc = SimpleNamespace(name="file", is_private=False, get_doc_before_save=lambda: None)
		with self.assertRaises(Exception):
			protect_file(doc)
		doc.is_private = True
		with self.assertRaises(Exception):
			protect_file(doc, "on_trash")

	@patch.object(api, "_owned")
	@patch.object(api, "_content")
	def test_preview_path_must_be_on_statement_allowlist(self, content, owned):
		owned.return_value = SimpleNamespace(report='{"statements":["problem_statement/problem.pdf"]}')
		with self.assertRaises(Exception):
			api.preview_statement("I1", "data/secret/01.in")
		content.assert_not_called()


class TestPackageSerialization(TestCase):
	def test_testcase_text_survives_document_html_sanitization(self):
		from frappe.utils.html_utils import sanitize_html

		payload = {
			"cases": [{
				"input": '<a> 0 ### 1\n<liws> 50.878158 ### 90\n',
				"expected_output": '<script>text, not markup</script> &amp; 中文\n',
			}],
		}
		encoded = api._json(payload)
		stored = sanitize_html(encoded)
		self.assertEqual(stored, encoded)
		self.assertEqual(json.loads(stored), payload)
		self.assertEqual(api._json(json.loads(stored)), encoded)

	def test_literal_unicode_escape_is_not_decoded_twice(self):
		payload = {"input": r"\u003citem\u003e", "output": "<item> & >"}
		self.assertEqual(json.loads(api._json(payload)), payload)
