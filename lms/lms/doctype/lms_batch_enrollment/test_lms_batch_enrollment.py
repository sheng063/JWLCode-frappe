# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from lms.lms.test_helpers import BaseTestUtils

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestLMSBatchEnrollment(UnitTestCase):
	"""
	Unit tests for LMSBatchEnrollment.
	Use this class for testing individual functions and methods.
	"""

	pass


class IntegrationTestLMSBatchEnrollment(IntegrationTestCase):
	"""
	Integration tests for LMSBatchEnrollment.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestLMSBatchEnrollmentCourseSync(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(8)
		self.instructor = self._create_user(
			f"batch-sync-instructor-{suffix}@example.com", "Batch", "Instructor", ["Course Creator"]
		)
		self.student = self._create_user(
			f"batch-sync-student-{suffix}@example.com", "Batch", "Student", ["LMS Student"]
		)
		self._create_evaluator(self.instructor.name)
		self.first_course = self._create_course(
			title=f"Batch Sync Course One {suffix}", instructor=self.instructor.name
		)
		self.second_course = self._create_course(
			title=f"Batch Sync Course Two {suffix}", instructor=self.instructor.name
		)
		self.batch = self._create_batch(
			self.first_course.name,
			instructor=self.instructor.name,
			title=f"Batch Enrollment Sync {suffix}",
			evaluator=self.instructor.name,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_adding_and_removing_a_student_syncs_batch_course_enrollment(self):
		batch_enrollment = self._create_batch_enrollment(self.student.name, self.batch.name)
		filters = {"member": self.student.name, "course": self.first_course.name}
		self.assertTrue(frappe.db.exists("LMS Enrollment", filters))

		batch_enrollment.delete()
		self.assertFalse(frappe.db.exists("LMS Enrollment", filters))

	def test_adding_and_removing_a_course_syncs_current_students(self):
		self._create_batch_enrollment(self.student.name, self.batch.name)
		filters = {"member": self.student.name, "course": self.second_course.name}
		self.assertFalse(frappe.db.exists("LMS Enrollment", filters))

		self.batch.append("courses", {"course": self.second_course.name, "evaluator": self.instructor.name})
		self.batch.save()
		self.assertTrue(frappe.db.exists("LMS Enrollment", filters))

		batch_course = frappe.db.get_value(
			"Batch Course", {"parent": self.batch.name, "course": self.second_course.name}, "name"
		)
		frappe.delete_doc("Batch Course", batch_course)
		self.assertFalse(frappe.db.exists("LMS Enrollment", filters))
