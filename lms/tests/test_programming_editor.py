import ast
import subprocess
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from lms.lms.programming_editor import format_code


def reject(message, *args):
	raise ValueError(message)


class TestProgrammingEditor(TestCase):
	def setUp(self):
		for target, value in (
			("session", SimpleNamespace(user="student@example.com")),
			("throw", reject),
		):
			mock = patch(f"lms.lms.programming_editor.frappe.{target}", value)
			mock.start()
			self.addCleanup(mock.stop)

	def test_formats_python_without_changing_program(self):
		source = "def solve( ):\n  text='a  b'\n  return [x*2 for x in range(3)]\n"
		formatted = format_code(source, "Python")
		self.assertIn("def solve():\n    text", formatted)
		self.assertEqual(ast.dump(ast.parse(source)), ast.dump(ast.parse(formatted)))
		self.assertEqual(format_code(formatted, "Python"), formatted)

	def test_formats_cpp_and_preserves_string_literals(self):
		source = '#include <string>\nint main(){std::string text="a  b";return 0;}'
		formatted = format_code(source, "C++", 4)
		self.assertIn('    std::string text = "a  b";', formatted)
		self.assertEqual(format_code(formatted, "C++", 4), formatted)

	def test_rejects_invalid_python_and_unsupported_inputs(self):
		for code, language, size in (("def :", "Python", 4), ("x", "Shell", 4), ("x", "C++", 3), ("x" * 200001, "Python", 4)):
			with self.subTest(language=language, size=size), self.assertRaises(ValueError):
				format_code(code, language, size)

	def test_guest_cannot_format(self):
		with patch("lms.lms.programming_editor.frappe.session", SimpleNamespace(user="Guest")):
			with self.assertRaises(ValueError):
				format_code("print(1)", "Python")

	def test_formatter_timeout_becomes_a_user_error(self):
		with patch("lms.lms.programming_editor.subprocess.run", side_effect=subprocess.TimeoutExpired("black", 10)):
			with self.assertRaises(ValueError):
				format_code("print(1)", "Python")
