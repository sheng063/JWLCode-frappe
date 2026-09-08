"""Completion rules: submitting a quiz and passing every programming exercise."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from lms.lms.doctype.course_lesson import course_lesson
from lms.lms.doctype.lms_quiz import lms_quiz


class TestLessonCompletion(unittest.TestCase):
	def setUp(self):
		self.user = patch.object(course_lesson.frappe, "session", SimpleNamespace(user="student@example.com"))
		self.user.start()
		self.addCleanup(self.user.stop)

	def test_quiz_submission_does_not_require_a_passing_score(self):
		details = SimpleNamespace(body=None, content=json.dumps({"blocks": [{"type": "quiz", "data": {"quiz": "Q1"}}]}), quiz_id=None)
		with patch.object(course_lesson.frappe.db, "get_value", return_value=details), patch.object(course_lesson.frappe.db, "exists", return_value=True) as exists:
			self.assertTrue(course_lesson.get_quiz_progress("L1"))
			exists.assert_called_once_with("LMS Quiz Submission", {"quiz": "Q1", "member": "student@example.com"})

	def test_legacy_quiz_id_requires_submission(self):
		details = SimpleNamespace(body=None, content=None, quiz_id="Q1")
		with patch.object(course_lesson.frappe.db, "get_value", return_value=details), patch.object(course_lesson.frappe.db, "exists", return_value=False):
			self.assertFalse(course_lesson.get_quiz_progress("L1"))

	def test_every_quiz_requires_submission(self):
		details = SimpleNamespace(body=None, content=json.dumps({"blocks": [{"type": "quiz", "data": {"quiz": q}} for q in ("Q1", "Q2")]}), quiz_id=None)
		with patch.object(course_lesson.frappe.db, "get_value", return_value=details), patch.object(course_lesson.frappe.db, "exists", side_effect=[True, False]):
			self.assertFalse(course_lesson.get_quiz_progress("L1"))

	def test_programming_requires_persisted_passed_submission(self):
		content = json.dumps({"blocks": [{"type": "program", "data": {"exercise": "E1"}}]})
		for passed in (False, True):
			with self.subTest(passed=passed), patch.object(course_lesson.frappe.db, "get_value", return_value=content), patch.object(course_lesson.frappe.db, "exists", return_value=passed) as exists:
				self.assertEqual(course_lesson.get_programming_progress("L1"), passed)
				exists.assert_called_once_with("LMS Programming Exercise Submission", {"exercise": "E1", "member": "student@example.com", "status": "Passed"})

	def test_all_programming_exercises_must_pass(self):
		content = json.dumps({"blocks": [{"type": "program", "data": {"exercise": e}} for e in ("E1", "E2")]})
		with patch.object(course_lesson.frappe.db, "get_value", return_value=content), patch.object(course_lesson.frappe.db, "exists", side_effect=[True, False]):
			self.assertFalse(course_lesson.get_programming_progress("L1"))

	def test_text_has_no_programming_gate(self):
		with patch.object(course_lesson.frappe.db, "get_value", return_value=None):
			self.assertTrue(course_lesson.get_programming_progress("L1"))

	def test_failed_quiz_score_still_updates_lesson(self):
		quiz = SimpleNamespace(lesson="L1", course="C1", passing_percentage=100)
		with patch("lms.lms.permissions.get_locked_lessons", return_value=[]), patch.object(lms_quiz, "save_progress") as save:
			lms_quiz.save_progress_after_quiz(quiz, 0)
			save.assert_called_once_with("L1", "C1")

	def test_submission_does_not_unlock_a_locked_lesson(self):
		quiz = SimpleNamespace(lesson="L1", course="C1", passing_percentage=100)
		with patch("lms.lms.permissions.get_locked_lessons", return_value=["L1"]), patch.object(lms_quiz, "save_progress") as save:
			lms_quiz.save_progress_after_quiz(quiz, 100)
			save.assert_not_called()
