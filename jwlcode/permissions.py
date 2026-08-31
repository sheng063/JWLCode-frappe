from __future__ import annotations

import frappe


ADMIN_ROLES = {"System Manager"}
TEACHER_ROLES = {"JWL Teacher", "JWL Content Manager"}


def roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def is_admin(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(ADMIN_ROLES & roles(user))


def is_campus_manager(user: str | None = None) -> bool:
	return "JWL Campus Manager" in roles(user)


def permitted_campuses(user: str | None = None) -> set[str]:
	user = user or frappe.session.user
	if is_admin(user):
		return set(frappe.get_all("JWL Campus", pluck="name"))
	return set(
		frappe.get_all(
			"User Permission",
			filters={"user": user, "allow": "JWL Campus", "apply_to_all_doctypes": 1},
			pluck="for_value",
		)
	)


def can_access_campus(campus: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	return is_admin(user) or (is_campus_manager(user) and campus in permitted_campuses(user))


def require_login() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("Authentication required", frappe.AuthenticationError)
	return user


def require_teacher() -> str:
	user = require_login()
	if not (is_admin(user) or is_campus_manager(user) or TEACHER_ROLES & roles(user)):
		frappe.throw("Teacher permission required", frappe.PermissionError)
	return user


def student_for_user(user: str | None = None) -> str | None:
	return frappe.db.get_value("JWL Student", {"user": user or frappe.session.user, "status": "Active"}, "name")


def teacher_for_user(user: str | None = None) -> str | None:
	return frappe.db.get_value("JWL Teacher", {"user": user or frappe.session.user, "status": "Active"}, "name")


def can_access_student(student: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_admin(user):
		return True
	student_campus = frappe.db.get_value("JWL Student", student, "campus")
	if student_campus and can_access_campus(student_campus, user):
		return True
	if student_for_user(user) == student:
		return True
	teacher = teacher_for_user(user)
	if not teacher:
		return False
	return bool(
		frappe.db.sql(
			"""
			select 1
			from `tabJWL Enrollment` e
			inner join `tabJWL Teaching Assignment` ta on ta.academic_class = e.academic_class
			where e.student = %s and e.status = 'Active'
			  and ta.teacher = %s and ta.status = 'Active'
			limit 1
			""",
			(student, teacher),
		)
	)


def can_access_course(course: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_admin(user):
		return True
	if is_campus_manager(user):
		campuses = tuple(permitted_campuses(user)) or ("",)
		return bool(
			frappe.db.sql(
				"""
				select 1 from `tabJWL Teaching Assignment` ta
				inner join `tabJWL Academic Class` c on c.name = ta.academic_class
				where ta.course = %(course)s and c.campus in %(campuses)s limit 1
				""",
				{"campuses": campuses, "course": course},
			)
		)
	teacher = teacher_for_user(user)
	if teacher and frappe.db.exists("JWL Course", {"name": course, "owner_teacher": teacher}):
		return True
	if teacher and frappe.db.exists("JWL Teaching Assignment", {"teacher": teacher, "course": course, "status": "Active"}):
		return True
	student = student_for_user(user)
	if not student:
		return False
	return bool(
		frappe.db.sql(
			"""
			select 1
			from `tabJWL Enrollment` e
			inner join `tabJWL Teaching Assignment` ta on ta.academic_class = e.academic_class
			where e.student = %s and e.status = 'Active'
			  and ta.course = %s and ta.status = 'Active'
			limit 1
			""",
			(student, course),
		)
	)


def require_course_access(course: str) -> None:
	if not can_access_course(course):
		frappe.throw("Course not found or access denied", frappe.PermissionError)


def require_class_teacher(academic_class: str) -> str:
	user = require_teacher()
	if is_admin(user):
		return user
	if is_campus_manager(user):
		campus = frappe.db.get_value("JWL Academic Class", academic_class, "campus")
		if campus and can_access_campus(campus, user):
			return user
	teacher = teacher_for_user(user)
	if not teacher or not frappe.db.exists(
		"JWL Teaching Assignment", {"teacher": teacher, "academic_class": academic_class, "status": "Active"}
	):
		frappe.throw("Class access denied", frappe.PermissionError)
	return user
