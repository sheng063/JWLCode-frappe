"""Course visibility hooks must preserve role-based mutation permissions."""

from unittest.mock import patch

import frappe

from lms.lms.course_access import has_permission
from lms.lms.test_helpers import BaseTestUtils
from lms.tests.test_course_visibility_and_batches import as_user


class TestCoursePermissions(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		frappe.db.savepoint("course_permissions_test")
		self.addCleanup(frappe.set_user, self.previous_user)
		self.addCleanup(frappe.db.rollback, save_point="course_permissions_test")
		for target in ("frappe.sendmail", "frappe.enqueue"):
			mock = patch(target)
			mock.start()
			self.addCleanup(mock.stop)
		self.suffix = frappe.generate_hash(length=8)

	def tearDown(self):
		# The savepoint rolls back fixtures, including failed mutation attempts.
		frappe.set_user("Administrator")

	def make_user(self, role):
		return self._create_user(
			f"course-permissions-{role.replace(' ', '-').lower()}-{self.suffix}@example.com",
			"Course",
			"Permissions",
			[role],
			user_type="System User",
		)

	def new_course(self, instructor):
		return frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": f"Permissions {frappe.generate_hash(length=10)}",
				"short_introduction": "Permission regression test",
				"description": "Permission regression test",
				"published": 0,
				"is_public": 0,
				"instructors": [{"instructor": instructor}],
			}
		)

	def test_authorized_roles_can_create_save_and_delete_private_drafts(self):
		for role in ("System Manager", "Moderator", "Course Creator"):
			with self.subTest(role=role):
				user = self.make_user(role)
				with as_user(user.name):
					course = self.new_course(user.name).insert()
					course.short_introduction = "Updated introduction"
					course.save()
					self.assertEqual(course.reload().short_introduction, "Updated introduction")
					course.delete()
					self.assertFalse(frappe.db.exists("LMS Course", course.name))

	def test_visibility_does_not_grant_mutation_permissions(self):
		for role in ("LMS Student", "Batch Evaluator"):
			with self.subTest(role=role):
				user = self.make_user(role)
				course = self.new_course(user.name).insert()
				with as_user(user.name):
					self.assertTrue(has_permission(course, "read"))
					with self.assertRaises(frappe.PermissionError):
						self.new_course(user.name).insert()
					with self.assertRaises(frappe.PermissionError):
						course.short_introduction = "Unauthorized change"
						course.save()
					with self.assertRaises(frappe.PermissionError):
						course.delete()

	def test_private_course_remains_hidden_from_unrelated_students_and_guests(self):
		student = self.make_user("LMS Student")
		course = self.new_course("Administrator").insert()
		for user in (student.name, "Guest"):
			for ptype in ("read", "select", "print", "export"):
				with self.subTest(user=user, ptype=ptype):
					self.assertFalse(has_permission(course, ptype, user))
