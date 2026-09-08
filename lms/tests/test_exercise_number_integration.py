"""Run against a migrated site; all fixture writes are rolled back."""
from unittest import TestCase

import frappe

from lms.lms.api import get_programming_exercise_count
from lms.patches.v2_0.add_exercise_numbers import execute


class TestExerciseNumber(TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.db.rollback()

	def exercise(self):
		return frappe.get_doc({"doctype": "LMS Programming Exercise", "title": "Number fixture",
			"problem_statement": "Example", "test_cases": [{"input": "1", "expected_output": "1"}]}).insert()

	def test_numbers_survive_deletion_and_edits_and_are_searchable(self):
		first, second = self.exercise(), self.exercise()
		assert first.exercise_number != second.exercise_number
		number = second.exercise_number
		frappe.delete_doc(first.doctype, first.name)
		third = self.exercise()
		assert int(third.exercise_number.split("-")[1]) > int(number.split("-")[1])
		second.title = "Renamed fixture"
		second.save()
		assert second.exercise_number == number
		assert get_programming_exercise_count(number) == 1
		assert frappe.get_list(second.doctype, or_filters={"title": ["like", f"%{number}%"], "exercise_number": ["like", f"%{number}%"]})[0].name == second.name
		second.exercise_number = "P-999999"
		with self.assertRaises(frappe.ValidationError):
			second.save()

	def test_backfill_is_repeatable_and_copy_gets_new_number(self):
		doc = self.exercise()
		number = doc.exercise_number
		copy = frappe.copy_doc(doc).insert()
		assert copy.exercise_number != number
		frappe.db.set_value(doc.doctype, doc.name, "exercise_number", None)
		execute()
		doc.reload()
		assert doc.exercise_number and doc.exercise_number != number
		execute()
		assert frappe.db.get_value(doc.doctype, doc.name, "exercise_number") == doc.exercise_number
