from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from lms.lms.judge_service import (
	STATUS_LABELS,
	_apply_result,
	_test_cases,
	run_programming_exercise,
)


class TestJudgeService(TestCase):
	@patch("lms.lms.judge_service.frappe.get_all")
	def test_combines_visible_and_protected_test_cases(self, get_all):
		exercise = SimpleNamespace(
			name="EX-1",
			test_cases=[SimpleNamespace(input="1", expected_output="2")],
		)
		get_all.return_value = [SimpleNamespace(input="3", expected_output="4", hidden=1)]

		assert _test_cases(exercise) == [
			{"input": "1", "expected_output": "2", "hidden": False},
			{"input": "3", "expected_output": "4", "hidden": True},
		]

	def test_applies_normalized_result_to_submission(self):
		doc = SimpleNamespace(
			judge_request_id=None,
			status="Queued",
			status_version=0,
			event_id=None,
			score=0,
			time_ms=0,
			memory_kb=0,
			compiler_message=None,
			exercise="EX-1",
			set=Mock(),
			append=Mock(),
			save=Mock(),
		)
		_apply_result(
			doc,
			{
				"judge_request_id": "REQ-1",
				"status": "ACCEPTED",
				"status_version": 1,
				"event_id": "REQ-1:1",
				"score": 100,
				"time_ms": 42,
				"memory_kb": 8192,
				"compiler_message": None,
			},
		)

		assert doc.status == STATUS_LABELS["ACCEPTED"]
		assert doc.judge_request_id == "REQ-1"
		assert doc.score == 100
		doc.set.assert_called_once_with("test_cases", [])
		doc.append.assert_not_called()
		doc.save.assert_called_once_with(ignore_permissions=True)

	@patch("lms.lms.judge_service._test_cases")
	@patch("lms.lms.judge_service.frappe.get_doc")
	def test_reveals_only_the_first_failed_hidden_case(self, get_doc, test_cases):
		get_doc.return_value = SimpleNamespace(name="EX-1")
		test_cases.return_value = [
			{"input": "public", "expected_output": "ok", "hidden": False},
			{"input": "first", "expected_output": "one", "hidden": True},
			{"input": "second", "expected_output": "two", "hidden": True},
		]
		doc = SimpleNamespace(
			judge_request_id=None, status="Queued", status_version=0, event_id=None,
			score=0, time_ms=0, memory_kb=0, compiler_message=None, exercise="EX-1",
			set=Mock(), append=Mock(), save=Mock(),
		)

		_apply_result(doc, {
			"judge_request_id": "REQ-1", "status": "WRONG_ANSWER",
			"status_version": 1, "event_id": "REQ-1:1", "score": 33.33,
			"time_ms": 42, "memory_kb": 8192, "compiler_message": None,
			"cases": [
				{"index": 1, "status": "Accepted"},
				{"index": 2, "status": "Wrong Answer", "stdout": "actual"},
				{"index": 3, "status": "Wrong Answer", "stdout": "also actual"},
			],
		})

		doc.append.assert_called_once_with("test_cases", {
			"input": "first", "expected_output": "one", "output": "actual",
			"status": "Failed", "hidden": 1,
		})

	@patch("lms.lms.judge_service.requests.post")
	@patch("lms.lms.judge_service.frappe.get_doc")
	@patch("lms.lms.judge_service._get_settings")
	@patch("lms.lms.judge_service._validate_submission_access")
	def test_run_uses_visible_cases_without_creating_submission(
		self, validate, get_settings, get_doc, post
	):
		get_settings.return_value = SimpleNamespace(
			service_url="http://judge",
			request_timeout_seconds=15,
			get_password=lambda _field: "token",
		)
		get_doc.return_value = SimpleNamespace(
			language="C++",
			time_limit_seconds=2,
			memory_limit_kb=128000,
			test_cases=[
				SimpleNamespace(input="1", expected_output="2"),
			],
		)
		response = Mock()
		response.json.return_value = {"status": "ACCEPTED", "cases": []}
		post.return_value = response

		result = run_programming_exercise("EX-1", "int main() {}")

		validate.assert_called_once_with("EX-1", "int main() {}", "Python")
		response.raise_for_status.assert_called_once_with()
		payload = post.call_args.kwargs["json"]
		assert payload["language"] == "Python"
		assert payload["source_code"] == "int main() {}"
		assert payload["test_cases"] == [{"input": "1", "expected_output": "2", "hidden": False}]



class TestPackageJudgeService(TestCase):
	def make_doc(self):
		return SimpleNamespace(
			name="SUB-1", package_version="V1", config_digest="digest", attempt_id="attempt",
			judge_request_id="REQ-1", status_version=0, event_id=None,
			flags=SimpleNamespace(), set=Mock(), append=Mock(), save=Mock(), reload=Mock(),
		)

	def result(self, status="WRONG_ANSWER"):
		return {"package_version": "V1", "config_digest": "digest", "attempt_id": "attempt",
			"judge_request_id": "REQ-1", "status_version": 1, "event_id": "event",
			"status": status, "score": 50, "compiler_message": "SECRET diagnostic",
			"cases": [{"case_id": "secret/01", "status": "Wrong Answer", "stdout": "SECRET"}]}

	@patch("lms.lms.judge_service.frappe.get_doc")
	def test_strict_feedback_never_persists_secret_or_partial_score(self, get_doc):
		get_doc.return_value = SimpleNamespace(cases='[{"case_id":"secret/01"}]')
		doc = self.make_doc()
		_apply_result(doc, self.result())
		assert doc.score == 0
		assert doc.compiler_message is None
		doc.append.assert_not_called()
		doc.set.assert_called_once_with("test_cases", [])

	@patch("lms.lms.judge_service.frappe.get_doc")
	def test_rejects_old_attempt_wrong_version_and_unknown_case(self, get_doc):
		get_doc.return_value = SimpleNamespace(cases='[{"case_id":"secret/01"}]')
		for key in ("attempt_id", "package_version", "config_digest", "judge_request_id"):
			doc, result = self.make_doc(), self.result()
			result[key] = "old"
			with self.assertRaises(Exception):
				_apply_result(doc, result)
			doc.save.assert_not_called()
		result = self.result()
		result["cases"][0]["case_id"] = "other"
		with self.assertRaises(Exception):
			_apply_result(self.make_doc(), result)

	@patch("lms.lms.judge_service.frappe.get_doc")
	def test_accepted_requires_complete_results(self, get_doc):
		get_doc.return_value = SimpleNamespace(cases='[{"case_id":"secret/01"}]')
		result = self.result("ACCEPTED")
		with self.assertRaises(Exception):
			_apply_result(self.make_doc(), result)
		result["cases"][0]["status"] = "Accepted"
		doc = self.make_doc()
		_apply_result(doc, result)
		assert doc.score == 100

	def test_payload_uses_stored_version_and_filters_public_run(self):
		import json
		from lms.lms.judge_service import _package_payload
		config = dict(protocol_version="icpc-legacy-v1", comparison_mode="icpc_default", validator_flags=[],
			scoring_mode="icpc", language="Python", time_limit_seconds=3, memory_limit_kb=131072)
		cases = [dict(case_id="sample", input="1", expected_output="", hidden=False),
			dict(case_id="secret", input="SECRET", expected_output="answer", hidden=True)]
		version = SimpleNamespace(name="V1", config_digest="digest", judge_config=json.dumps(config), cases=json.dumps(cases))
		assert len(_package_payload(version)["test_cases"]) == 2
		public = _package_payload(version, public_only=True)
		assert public["test_cases"] == cases[:1]
		assert public["time_limit_seconds"] == 3
