import frappe
from frappe.model.document import Document

from lms.lms.problem_package.permissions import INTERNAL_WRITE


class LMSProblemPackageImport(Document):
	def validate(self):
		if self.flags.package_service is not INTERNAL_WRITE:
			frappe.throw("Package records can only be changed through the import service.")

	def on_trash(self):
		frappe.throw("Package records must be retained for submission history.")
