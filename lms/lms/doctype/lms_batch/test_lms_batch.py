# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import frappe

from lms.lms.api import add_batch_course
from lms.lms.test_helpers import BaseTestUtils


class TestLMSBatch(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(8)
		self.instructor = self._create_user(
			f"batch-course-{suffix}@example.com", "Batch", "Instructor", ["Course Creator"]
		)
		self._create_evaluator(self.instructor.name)
		first_course = self._create_course(
			title=f"Batch Course One {suffix}", instructor=self.instructor.name
		)
		self.second_course = self._create_course(
			title=f"Batch Course Two {suffix}", instructor=self.instructor.name
		)
		self.batch = self._create_batch(
			first_course.name,
			instructor=self.instructor.name,
			title=f"Batch Course Persistence {suffix}",
			evaluator=self.instructor.name,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_add_batch_course_persists_child_row_on_parent(self):
		frappe.set_user(self.instructor.name)

		row = add_batch_course(self.batch.name, self.second_course.name)

		reloaded = frappe.get_doc("LMS Batch", self.batch.name)
		matching = [course for course in reloaded.courses if course.course == self.second_course.name]
		self.assertEqual(len(matching), 1)
		self.assertEqual(row["name"], matching[0].name)
		self.assertFalse(matching[0].is_new())

	def test_add_batch_course_rejects_user_without_batch_permission(self):
		outsider = self._create_user(
			f"batch-outsider-{frappe.generate_hash(8)}@example.com",
			"Batch",
			"Outsider",
			["LMS Student"],
		)
		frappe.set_user(outsider.name)

		with self.assertRaises(frappe.PermissionError):
			add_batch_course(self.batch.name, self.second_course.name)

		self.assertFalse(
			frappe.db.exists(
				"Batch Course", {"parent": self.batch.name, "course": self.second_course.name}
			)
		)
