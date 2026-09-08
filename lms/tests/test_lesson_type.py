import unittest

from lms.lms.lesson_type import resolve_lesson_type


class TestLessonType(unittest.TestCase):
	def setUp(self):
		self.program = {"type": "program", "data": {"exercise": "exercise-1"}}
		self.text = {"type": "markdown", "data": {"text": "Hello"}}

	def test_legacy_content_infers_type(self):
		self.assertEqual(resolve_lesson_type([self.program]), "Programming")
		self.assertEqual(resolve_lesson_type([self.text]), "Text")

	def test_empty_draft_retains_selected_type(self):
		self.assertEqual(resolve_lesson_type([], "Programming"), "Programming")

	def test_mixed_blocks_are_rejected(self):
		for other in (self.text, {"type": "quiz", "data": {"quiz": "quiz-1"}}, {"type": "upload"}):
			with self.subTest(other=other), self.assertRaises(ValueError):
				resolve_lesson_type([self.program, other])

	def test_selected_type_is_enforced(self):
		for blocks, kind in (([self.program], "Text"), ([self.text], "Programming"), ([], "Other")):
			with self.subTest(kind=kind), self.assertRaises(ValueError):
				resolve_lesson_type(blocks, kind)

	def test_legacy_fields_cannot_bypass_validation(self):
		for field in ("body", "youtube", "quiz_id", "question"):
			with self.subTest(field=field), self.assertRaises(ValueError):
				resolve_lesson_type([self.program], **{field: "legacy content"})

	def test_padding_is_ignored(self):
		self.assertEqual(resolve_lesson_type([self.program, {"type": "paragraph", "data": {"text": "<br>&nbsp; "}}]), "Programming")

	def test_empty_exercise_is_rejected(self):
		with self.assertRaises(ValueError):
			resolve_lesson_type([{"type": "program", "data": {}}], "Programming")

	def test_raw_text_cannot_bypass_programming_type(self):
		for content in ('Hello', '"Hello"', '{"blocks":"Hello"}'):
			with self.subTest(content=content), self.assertRaises(ValueError):
				resolve_lesson_type([], "Programming", raw_content=content)
