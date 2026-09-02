# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from lms.lms.batch_enrollment_sync import (
	enroll_member_in_batch_course,
	remove_member_from_batch_course,
)


class BatchCourse(Document):
	def after_insert(self):
		self.sync_enrollments(enroll_member_in_batch_course)

	def on_trash(self):
		self.sync_enrollments(remove_member_from_batch_course)

	def sync_enrollments(self, sync_member):
		members = frappe.get_all("LMS Batch Enrollment", {"batch": self.parent}, pluck="member")
		for member in members:
			sync_member(self.parent, member, self.course)
