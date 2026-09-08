"""Portal visibility and the union of a student's batch course registrations."""

from contextlib import contextmanager
from unittest.mock import patch

import frappe

from lms.lms.api import add_batch_course
from lms.lms.batch_progress import get_student_progress
from lms.lms.course_access import can_view_course, get_visible_courses
from lms.lms.permissions import can_access_lesson
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_course_count, get_course_details, get_course_outline, get_courses


@contextmanager
def as_user(user):
	previous = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(previous)


class BatchVisibilityFixtures(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.savepoint = "course_visibility_test"
		frappe.db.savepoint(self.savepoint)
		for target in ("frappe.sendmail", "frappe.enqueue"):
			mock = patch(target)
			mock.start()
			self.addCleanup(mock.stop)
		self.suffix = frappe.generate_hash(length=8)
		self.student = self._create_user(
			f"visibility-{self.suffix}@example.com", "Visibility", "Student", ["LMS Student"]
		)
		self.public = self._create_course(
			title=f"Visibility Public {self.suffix}", instructor="Administrator"
		)
		self.private = self._create_course(
			title=f"Visibility Private {self.suffix}", instructor="Administrator"
		)
		self.private.is_public = 0
		self.private.save()
		self._create_evaluator("Administrator")
		self.batch = self._create_batch(
			course=self.private.name,
			title=f"Visibility Batch {self.suffix}",
			instructor="Administrator",
			evaluator="Administrator",
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point=self.savepoint)

	def enrollment(self, course=None):
		return frappe.db.get_value(
			"LMS Enrollment",
			{"course": course or self.private.name, "member": self.student.name},
			["name", "enrollment_from_batch", "progress"],
			as_dict=True,
		)

	def second_batch(self):
		return self._create_batch(
			course=self.private.name,
			title=f"Visibility Second {self.suffix}",
			instructor="Administrator",
			evaluator="Administrator",
		)


class TestCourseVisibilityAndBatches(BatchVisibilityFixtures):
	def test_public_visible_and_private_hidden_before_registration(self):
		with as_user(self.student.name):
			self.assertTrue(can_view_course(self.public.name))
			self.assertFalse(can_view_course(self.private.name))
			self.assertEqual(get_course_details(self.private.name), {})
			self.assertEqual(get_course_outline(self.private.name), [])
			self.assertEqual(get_course_details(self.public.name).name, self.public.name)
			rows = get_visible_courses(
				filters={"name": ["in", [self.public.name, self.private.name]]}, pluck="name"
			)
			self.assertEqual(rows, [self.public.name])

	def test_catalog_pagination_and_count_exclude_private_featured_courses(self):
		frappe.db.set_value("LMS Course", self.private.name, {"featured": 1, "enrollments": 100})
		with as_user(self.student.name):
			filters = {"title": ["like", f"%{self.suffix}%"], "live": 1}
			rows = get_courses(filters=filters.copy(), start=0, limit_page_length=1)
			self.assertEqual([row.name for row in rows], [self.public.name])
			self.assertEqual(get_course_count(filters=filters.copy()), 1)
			self.assertEqual(get_courses(filters=filters.copy(), start=1, limit_page_length=1), [])

	def test_private_preview_lesson_is_not_a_bypass(self):
		chapter = self._create_chapter(f"Visibility Chapter {self.suffix}", self.private.name)
		lesson = self._create_lesson(f"Visibility Lesson {self.suffix}", chapter.name, self.private.name)
		frappe.db.set_value("Course Lesson", lesson.name, "include_in_preview", 1)
		with as_user(self.student.name):
			self.assertFalse(can_access_lesson(lesson.name))
		self._create_batch_enrollment(self.student.name, self.batch.name)
		with as_user(self.student.name):
			self.assertTrue(can_access_lesson(lesson.name))
			self.assertEqual(get_course_details(self.private.name).name, self.private.name)

	def test_private_course_cannot_be_self_enrolled(self):
		with as_user(self.student.name), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{"doctype": "LMS Enrollment", "member": self.student.name, "course": self.private.name}
			).insert()

	def test_batch_enrolls_private_course_even_when_self_learning_disabled(self):
		frappe.db.set_value("LMS Course", self.private.name, "disable_self_learning", 1)
		self._create_batch_enrollment(self.student.name, self.batch.name)
		self.assertEqual(self.enrollment().enrollment_from_batch, self.batch.name)

	def test_self_enrolled_batch_can_register_its_private_courses(self):
		frappe.db.set_value("LMS Course", self.private.name, {"disable_self_learning": 1, "paid_course": 1})
		frappe.db.set_value("LMS Batch", self.batch.name, "allow_self_enrollment", 1)
		with as_user(self.student.name):
			self._create_batch_enrollment(self.student.name, self.batch.name)
		self.assertEqual(self.enrollment().enrollment_from_batch, self.batch.name)

	def test_shared_course_transfers_source_and_preserves_progress(self):
		other = self.second_batch()
		first_membership = self._create_batch_enrollment(self.student.name, self.batch.name)
		second_membership = self._create_batch_enrollment(self.student.name, other.name)
		original = self.enrollment()
		frappe.db.set_value("LMS Enrollment", original.name, "progress", 75)
		frappe.delete_doc("LMS Batch Enrollment", first_membership.name)
		current = self.enrollment()
		self.assertEqual(current.name, original.name)
		self.assertEqual(current.progress, 75)
		self.assertEqual(current.enrollment_from_batch, other.name)
		frappe.delete_doc("LMS Batch Enrollment", second_membership.name)
		self.assertIsNone(self.enrollment())
		with as_user(self.student.name):
			self.assertFalse(can_view_course(self.private.name))

	def test_removing_non_source_batch_keeps_original_enrollment(self):
		other = self.second_batch()
		self._create_batch_enrollment(self.student.name, self.batch.name)
		membership = self._create_batch_enrollment(self.student.name, other.name)
		frappe.delete_doc("LMS Batch Enrollment", membership.name)
		self.assertEqual(self.enrollment().enrollment_from_batch, self.batch.name)

	def test_parent_course_table_updates_register_and_unregister_members(self):
		self._create_batch_enrollment(self.student.name, self.batch.name)
		add_batch_course(self.batch.name, self.public.name)
		self.assertIsNotNone(self.enrollment(self.public.name))
		self.batch.reload()
		self.batch.set("courses", [row for row in self.batch.courses if row.course != self.public.name])
		self.batch.save()
		self.assertIsNone(self.enrollment(self.public.name))
		self.assertIsNotNone(self.enrollment())

	def test_removing_shared_course_from_parent_preserves_other_source(self):
		other = self.second_batch()
		self._create_batch_enrollment(self.student.name, self.batch.name)
		self._create_batch_enrollment(self.student.name, other.name)
		self.batch.reload()
		self.batch.set("courses", [])
		self.batch.save()
		self.assertEqual(self.enrollment().enrollment_from_batch, other.name)

	def test_direct_child_course_removal_synchronizes_members(self):
		self._create_batch_enrollment(self.student.name, self.batch.name)
		frappe.delete_doc("Batch Course", self.batch.courses[0].name)
		self.assertIsNone(self.enrollment())

	def test_independent_registration_survives_batch_removal(self):
		self._create_enrollment(self.student.name, self.private.name)
		membership = self._create_batch_enrollment(self.student.name, self.batch.name)
		frappe.delete_doc("LMS Batch Enrollment", membership.name)
		self.assertIsNotNone(self.enrollment())
		self.assertFalse(self.enrollment().enrollment_from_batch)

	def test_student_cannot_retarget_registration_to_private_course(self):
		self._create_enrollment(self.student.name, self.public.name)
		with as_user(self.student.name), self.assertRaises(frappe.PermissionError):
			doc = frappe.get_doc("LMS Enrollment", self.enrollment(self.public.name).name)
			doc.course = self.private.name
			doc.save()

	def test_student_cannot_clear_batch_source(self):
		self._create_batch_enrollment(self.student.name, self.batch.name)
		with as_user(self.student.name), self.assertRaises(frappe.PermissionError):
			doc = frappe.get_doc("LMS Enrollment", self.enrollment().name)
			doc.enrollment_from_batch = None
			doc.save()

	def test_student_cannot_fake_batch_membership(self):
		with as_user(self.student.name), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "LMS Enrollment",
					"member": self.student.name,
					"course": self.private.name,
					"enrollment_from_batch": self.batch.name,
				}
			).insert()

	def test_progress_uses_every_course_including_unstarted_courses(self):
		self._create_batch_enrollment(self.student.name, self.batch.name)
		add_batch_course(self.batch.name, self.public.name)
		frappe.db.set_value("LMS Enrollment", self.enrollment().name, "progress", 80)
		data = get_student_progress(self.batch.name, [self.student.name])
		self.assertEqual(data[self.student.name], {"course_progress": 40, "programming_pass_rate": 0})

	def test_progress_rejects_students_and_excludes_other_batches_members(self):
		with as_user(self.student.name), self.assertRaises(frappe.PermissionError):
			get_student_progress(self.batch.name, [self.student.name])
		self.assertEqual(get_student_progress(self.batch.name, [self.student.name]), {})

	def test_empty_batch_progress_is_zero(self):
		self._create_batch_enrollment(self.student.name, self.batch.name)
		self.batch.reload()
		self.batch.set("courses", [])
		self.batch.save()
		self.assertEqual(
			get_student_progress(self.batch.name, [self.student.name])[self.student.name],
			{"course_progress": 0, "programming_pass_rate": 0},
		)

	def test_programming_rate_counts_unique_passed_exercises_not_submissions(self):
		import json

		self._create_batch_enrollment(self.student.name, self.batch.name)
		add_batch_course(self.batch.name, self.public.name)
		exercises = [f"visibility-exercise-{self.suffix}-{index}" for index in range(3)]
		for name in exercises:
			frappe.get_doc(
				{
					"doctype": "LMS Programming Exercise",
					"name": name,
					"title": name,
					"problem_statement": "Solve",
					"language": "Python",
				}
			).db_insert()
		for index, (course, exercise) in enumerate(
			[
				(self.private.name, exercises[0]),
				(self.public.name, exercises[0]),
				(self.public.name, exercises[1]),
			]
		):
			chapter = self._create_chapter(f"Programming Chapter {self.suffix}-{index}", course)
			self._create_lesson(
				f"Programming Lesson {self.suffix}-{index}",
				chapter.name,
				course,
				content=json.dumps({"blocks": [{"type": "program", "data": {"exercise": exercise}}]}),
			)
		for exercise, status in [
			(exercises[0], "Passed"),
			(exercises[0], "Passed"),
			(exercises[0], "Failed"),
			(exercises[1], "Failed"),
			(exercises[2], "Passed"),
		]:
			frappe.get_doc(
				{
					"doctype": "LMS Programming Exercise Submission",
					"member": self.student.name,
					"exercise": exercise,
					"status": status,
					"code": "print(1)",
				}
			).db_insert()
		data = get_student_progress(self.batch.name, [self.student.name])
		self.assertEqual(data[self.student.name]["programming_pass_rate"], 50)

	def test_guest_cannot_see_private_course_or_outline(self):
		with as_user("Guest"), patch("lms.lms.utils.guest_access_allowed", return_value=True):
			self.assertEqual(get_course_details(self.private.name), {})
			self.assertEqual(get_course_outline(self.private.name), [])
			self.assertEqual(get_visible_courses(filters={"name": self.private.name}), [])

	def test_batch_overview_does_not_reveal_private_course_to_non_member(self):
		from lms.lms.utils import get_batch_details

		with as_user(self.student.name):
			self.assertEqual(get_batch_details(self.batch.name).courses, [])

	def test_batch_course_list_hides_private_course_from_non_member(self):
		from lms.lms.utils import get_batch_course_rows

		with as_user(self.student.name):
			rows = get_batch_course_rows(filters={"parent": self.batch.name})
			self.assertEqual(rows, [])

	def test_deleting_a_batch_preserves_only_remaining_sources(self):
		from lms.lms.api import delete_batch

		other = self.second_batch()
		self._create_batch_enrollment(self.student.name, self.batch.name)
		self._create_batch_enrollment(self.student.name, other.name)
		delete_batch(self.batch.name)
		self.assertEqual(self.enrollment().enrollment_from_batch, other.name)
		delete_batch(other.name)
		self.assertIsNone(self.enrollment())

	def test_migration_repairs_missing_and_stale_sources_idempotently(self):
		from lms.lms.batch_enrollment_sync import reconcile_batch_course_enrollments

		self._create_batch_enrollment(self.student.name, self.batch.name)
		frappe.db.delete("LMS Enrollment", {"name": self.enrollment().name})
		reconcile_batch_course_enrollments()
		first = self.enrollment()
		self.assertEqual(first.enrollment_from_batch, self.batch.name)
		reconcile_batch_course_enrollments()
		self.assertEqual(self.enrollment().name, first.name)
		frappe.db.delete("Batch Course", {"parent": self.batch.name})
		reconcile_batch_course_enrollments()
		self.assertIsNone(self.enrollment())
