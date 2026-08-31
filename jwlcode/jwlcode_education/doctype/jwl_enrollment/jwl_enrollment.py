from frappe.model.document import Document

import frappe
from frappe.utils import getdate


class JWLEnrollment(Document):
	def validate(self):
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw("End date cannot be earlier than start date")
		filters = {
			"student": self.student,
			"academic_class": self.academic_class,
			"status": "Active",
			"name": ["!=", self.name or ""],
		}
		if self.status == "Active" and frappe.db.exists("JWL Enrollment", filters):
			frappe.throw("The student already has an active enrollment in this class")

