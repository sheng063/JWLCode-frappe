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

