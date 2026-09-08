# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname

from lms.lms.problem_package.permissions import INTERNAL_WRITE


class LMSProgrammingExercise(Document):
	def before_insert(self):
		self.exercise_number = make_autoname("P-.######")

	def validate(self):
		old = self.get_doc_before_save()
		if old and self.exercise_number != old.exercise_number:
			frappe.throw(_("Exercise number cannot be changed."))
		if self.flags.package_service is not INTERNAL_WRITE:
			if not old and (
				self.active_package_version
				or self.source_type == "icpc"
				or self.scoring_mode == "icpc"
				or self.feedback_policy == "strict"
			):
				frappe.throw("Package settings require the import service.")
			protected = ("source_type", "active_package_version", "scoring_mode", "feedback_policy")
			if old and any(self.get(key) != old.get(key) for key in protected):
				frappe.throw("Package settings can only be changed by publishing a version.")
			if self.source_type == "icpc" or (old and old.source_type == "icpc"):
				frappe.throw("Import a new package version to modify this exercise.")
		self.validate_test_cases()

	def validate_test_cases(self):
		if self.source_type == "icpc" and self.flags.package_service is INTERNAL_WRITE:
			if not self.active_package_version:
				frappe.throw("An ICPC exercise requires a package version.")
			return
		for case in self.test_cases or []:
			if not case.expected_output:
				frappe.throw(_("Expected output is required for manual test cases."))
		if not self.test_cases:
			frappe.throw(_("At least one test case is required for the programming exercise."))
