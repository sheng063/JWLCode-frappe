from frappe.model.document import Document

import frappe
from frappe.utils import get_datetime


class JWLAssignment(Document):
	def validate(self):
		if get_datetime(self.opens_at) >= get_datetime(self.due_at):
			frappe.throw("Due time must be later than open time")
		if float(self.max_score or 0) <= 0:
			frappe.throw("Maximum score must be positive")

