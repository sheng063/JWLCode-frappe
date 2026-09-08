"""Server-only mutation token and denial hooks for retained package data."""

import frappe

INTERNAL_WRITE = object()


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	return user != "Guest" and (doc.owner == user or "System Manager" in frappe.get_roles(user))


def query_conditions(user=None):
	user = user or frappe.session.user
	if "System Manager" in frappe.get_roles(user):
		return ""
	return "owner = " + frappe.db.escape(user)


def protect_file(doc, method=None):
	if (
		not doc.name
		or not frappe.db.table_exists("LMS Problem Package Import")
		or not frappe.db.exists("LMS Problem Package Import", {"file_id": doc.name})
	):
		return
	old = doc.get_doc_before_save()
	if (
		method == "on_trash"
		or not doc.is_private
		or (
			old
			and any(
				doc.get(key) != old.get(key)
				for key in (
					"file_url",
					"content_hash",
					"is_private",
					"attached_to_doctype",
					"attached_to_name",
				)
			)
		)
	):
		frappe.throw("Imported package files must remain private and unchanged.")
