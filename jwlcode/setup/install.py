from __future__ import annotations

import frappe


ROLES = (
	"JWL Student",
	"JWL Teacher",
	"JWL Campus Manager",
	"JWL Content Manager",
	"JWL Judge Service",
)


def after_install() -> None:
	ensure_roles()
	ensure_indexes()


def ensure_roles() -> None:
	for role_name in ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)


def ensure_indexes() -> None:
	"""Enforce business keys atomically; controller checks provide friendly errors."""
	frappe.db.add_unique(
		"JWL Submission",
		["student", "client_request_id"],
		constraint_name="uniq_jwl_submission_request",
	)
	frappe.db.add_unique(
		"JWL Progress",
		["student", "lesson"],
		constraint_name="uniq_jwl_progress",
	)
