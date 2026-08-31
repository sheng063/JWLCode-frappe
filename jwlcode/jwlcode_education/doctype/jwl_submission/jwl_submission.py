from frappe.model.document import Document

import frappe


IMMUTABLE_FIELDS = {
	"student",
	"problem",
	"assignment",
	"submission_type",
	"language",
	"source_code",
	"custom_input",
	"client_request_id",
	"problem_version",
	"policy_snapshot",
	"test_case_ref",
	"test_case_checksum",
}


class JWLSubmission(Document):
	def validate(self):
		existing = frappe.db.get_value(
			"JWL Submission",
			{
				"student": self.student,
				"client_request_id": self.client_request_id,
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if existing:
			frappe.throw("client_request_id has already been used by this student")
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if before:
			for fieldname in IMMUTABLE_FIELDS:
				if before.get(fieldname) != self.get(fieldname):
					frappe.throw(f"Submission field {fieldname} is immutable")

