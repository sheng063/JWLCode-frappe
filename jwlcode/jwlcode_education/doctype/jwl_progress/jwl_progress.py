from frappe.model.document import Document

import frappe


class JWLProgress(Document):
	def validate(self):
		self.percent = max(0, min(float(self.percent or 0), 100))
		filters = {"student": self.student, "lesson": self.lesson, "name": ["!=", self.name or ""]}
		if frappe.db.exists("JWL Progress", filters):
			frappe.throw("Progress must be unique for each student and lesson")

