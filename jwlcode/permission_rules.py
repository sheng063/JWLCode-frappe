from __future__ import annotations

import frappe

from jwlcode.permissions import can_access_student, is_admin, permitted_campuses, student_for_user, teacher_for_user


def _escape(value: str) -> str:
	return frappe.db.escape(value)


def _may_access_sensitive(user: str | None, permission_type: str | None) -> bool:
	if permission_type in {None, "read", "select", "print", "email", "export"}:
		return True
	user = user or frappe.session.user
	return is_admin(user) or "JWL Campus Manager" in frappe.get_roles(user)


def student_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_admin(user):
		return ""
	student = student_for_user(user)
	if student:
		return f"`tabJWL Student`.`name` = {_escape(student)}"
	teacher = teacher_for_user(user)
	if teacher:
		return (
			"exists (select 1 from `tabJWL Enrollment` e "
			"inner join `tabJWL Teaching Assignment` ta on ta.academic_class=e.academic_class "
			f"where e.student=`tabJWL Student`.name and ta.teacher={_escape(teacher)} "
			"and e.status='Active' and ta.status='Active')"
		)
	campuses = permitted_campuses(user)
	if campuses:
		return f"`tabJWL Student`.`campus` in ({','.join(_escape(x) for x in campuses)})"
	return "1=0"


def enrollment_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_admin(user):
		return ""
	student = student_for_user(user)
	if student:
		return f"`tabJWL Enrollment`.`student` = {_escape(student)}"
	teacher = teacher_for_user(user)
	if teacher:
		return (
			"exists (select 1 from `tabJWL Teaching Assignment` ta "
			"where ta.academic_class=`tabJWL Enrollment`.academic_class "
			f"and ta.teacher={_escape(teacher)} and ta.status='Active')"
		)
	campuses = permitted_campuses(user)
	if campuses:
		return (
			"exists (select 1 from `tabJWL Academic Class` c "
			"where c.name=`tabJWL Enrollment`.academic_class "
			f"and c.campus in ({','.join(_escape(x) for x in campuses)}))"
		)
	return "1=0"


def class_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_admin(user):
		return ""
	teacher = teacher_for_user(user)
	if teacher:
		return (
			"exists (select 1 from `tabJWL Teaching Assignment` ta "
			"where ta.academic_class=`tabJWL Academic Class`.name "
			f"and ta.teacher={_escape(teacher)} and ta.status='Active')"
		)
	campuses = permitted_campuses(user)
	if campuses:
		return f"`tabJWL Academic Class`.`campus` in ({','.join(_escape(x) for x in campuses)})"
	return "1=0"


def submission_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_admin(user):
		return ""
	student = student_for_user(user)
	if student:
		return f"`tabJWL Submission`.`student` = {_escape(student)}"
	teacher = teacher_for_user(user)
	if teacher:
		return (
			"exists (select 1 from `tabJWL Enrollment` e "
			"inner join `tabJWL Teaching Assignment` ta on ta.academic_class=e.academic_class "
			"where e.student=`tabJWL Submission`.student "
			f"and ta.teacher={_escape(teacher)} and e.status='Active' and ta.status='Active')"
		)
	campuses = permitted_campuses(user)
	if campuses:
		return (
			"exists (select 1 from `tabJWL Student` s where s.name=`tabJWL Submission`.student "
			f"and s.campus in ({','.join(_escape(x) for x in campuses)}))"
		)
	return "1=0"


def progress_query(user: str | None = None) -> str:
	return submission_query(user).replace("`tabJWL Submission`", "`tabJWL Progress`")


def score_query(user: str | None = None) -> str:
	condition = submission_query(user)
	if not condition:
		return ""
	return (
		"exists (select 1 from `tabJWL Submission` "
		"where `tabJWL Submission`.name=`tabJWL Score`.submission "
		f"and ({condition}))"
	)


def score_adjustment_query(user: str | None = None) -> str:
	condition = score_query(user)
	if not condition:
		return ""
	return (
		"exists (select 1 from `tabJWL Score` where "
		"`tabJWL Score`.name=`tabJWL Score Adjustment`.score "
		f"and ({condition}))"
	)


def student_permission(doc, user=None, permission_type=None) -> bool:
	return _may_access_sensitive(user, permission_type) and can_access_student(doc.name, user)


def enrollment_permission(doc, user=None, permission_type=None) -> bool:
	return _may_access_sensitive(user, permission_type) and can_access_student(doc.student, user)


def progress_permission(doc, user=None, permission_type=None) -> bool:
	return _may_access_sensitive(user, permission_type) and can_access_student(doc.student, user)


def submission_permission(doc, user=None, permission_type=None) -> bool:
	return _may_access_sensitive(user, permission_type) and can_access_student(doc.student, user)


def score_permission(doc, user=None, permission_type=None) -> bool:
	student = frappe.db.get_value("JWL Submission", doc.submission, "student")
	return bool(_may_access_sensitive(user, permission_type) and student and can_access_student(student, user))


def score_adjustment_permission(doc, user=None, permission_type=None) -> bool:
	submission = frappe.db.get_value("JWL Score", doc.score, "submission")
	student = frappe.db.get_value("JWL Submission", submission, "student")
	return bool(_may_access_sensitive(user, permission_type) and student and can_access_student(student, user))


def class_permission(doc, user=None, permission_type=None) -> bool:
	user = user or frappe.session.user
	if not _may_access_sensitive(user, permission_type):
		return False
	if is_admin(user):
		return True
	teacher = teacher_for_user(user)
	if teacher and frappe.db.exists(
		"JWL Teaching Assignment", {"teacher": teacher, "academic_class": doc.name, "status": "Active"}
	):
		return True
	return doc.campus in permitted_campuses(user)
