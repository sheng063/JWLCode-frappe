from frappe.model.document import Document

import frappe


class JWLTeachingAssignment(Document):
	def validate(self):
		filters = {
			"teacher": self.teacher,
			"academic_class": self.academic_class,
			"course": self.course,
			"status": "Active",
			"name": ["!=", self.name or ""],
		}
		if self.status == "Active" and frappe.db.exists("JWL Teaching Assignment", filters):
			frappe.throw("This active teaching assignment already exists")

