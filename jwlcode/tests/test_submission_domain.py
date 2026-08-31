import unittest

from jwlcode.domain.submission import can_transition, is_terminal, normalize_languages, validate_source


class SubmissionDomainTest(unittest.TestCase):
	def test_happy_path_transitions(self):
		self.assertTrue(can_transition("QUEUED", "COMPILING"))
		self.assertTrue(can_transition("COMPILING", "RUNNING"))
		self.assertTrue(can_transition("RUNNING", "ACCEPTED"))

	def test_idempotent_transition_is_allowed(self):
		self.assertTrue(can_transition("RUNNING", "RUNNING"))

	def test_terminal_state_cannot_be_overwritten(self):
		self.assertFalse(can_transition("ACCEPTED", "RUNNING"))
		self.assertFalse(can_transition("WRONG_ANSWER", "ACCEPTED"))

	def test_illegal_shortcut_is_rejected(self):
		self.assertFalse(can_transition("QUEUED", "ACCEPTED"))

	def test_terminal_statuses(self):
		self.assertTrue(is_terminal("COMPILE_ERROR"))
		self.assertFalse(is_terminal("COMPILING"))

	def test_languages_are_normalized(self):
		self.assertEqual(normalize_languages("CPP17, cpp20\nC"), {"cpp17", "cpp20", "c"})

	def test_source_must_not_be_empty(self):
		with self.assertRaisesRegex(ValueError, "required"):
			validate_source("  ")

	def test_source_size_is_measured_in_bytes(self):
		with self.assertRaisesRegex(ValueError, "exceeds"):
			validate_source("中文", max_bytes=5)


if __name__ == "__main__":
	unittest.main()
