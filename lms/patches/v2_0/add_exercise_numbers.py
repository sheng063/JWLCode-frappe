import frappe
from frappe.model.naming import make_autoname


def execute():
	for row in frappe.get_all("LMS Programming Exercise", fields=["name", "exercise_number"], order_by="creation asc, name asc"):
		if not row.exercise_number:
			frappe.db.set_value("LMS Programming Exercise", row.name, "exercise_number", make_autoname("P-.######"), update_modified=False)
