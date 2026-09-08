"""Course visibility shared by catalog queries and direct reads."""

import frappe


def is_course_staff(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(
		{"System Manager", "Moderator", "Course Creator", "Batch Evaluator"} & set(frappe.get_roles(user))
	)


def can_view_course(course, user=None):
	user = user or frappe.session.user
	if is_course_staff(user):
		return True
	if frappe.db.exists("LMS Enrollment", {"course": course, "member": user}):
		return True
	if frappe.db.exists(
		"Course Instructor", {"parent": course, "parenttype": "LMS Course", "instructor": user}
	):
		return True
	return bool(frappe.db.exists("LMS Course", {"name": course, "published": 1, "is_public": 1}))


def has_permission(doc, ptype="read", user=None):
	if ptype in ("read", "select", "print", "export"):
		return can_view_course(doc.name, user)
	return None


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if is_course_staff(user):
		return ""
	user = frappe.db.escape(user)
	return f"""((`tabLMS Course`.published = 1 AND `tabLMS Course`.is_public = 1)
		OR `tabLMS Course`.name IN (SELECT course FROM `tabLMS Enrollment` WHERE member = {user})
		OR `tabLMS Course`.name IN (SELECT parent FROM `tabCourse Instructor`
			WHERE parenttype = 'LMS Course' AND instructor = {user}))"""


def get_visible_courses(
	*,
	filters=None,
	fields=None,
	or_filters=None,
	order_by=None,
	start=0,
	page_length=0,
	pluck=None,
	distinct=False,
):
	"""Portal reads use explicit fields and visibility instead of Desk role permissions.

	Students/guests have no general LMS Course read DocPerm. The custom portal
	API must still serve their allowed courses, applying the visibility condition
	in SQL before counting, ordering or limiting results.
	"""
	query = frappe.qb.get_query(
		"LMS Course",
		fields=[pluck] if pluck else fields,
		filters=filters,
		or_filters=or_filters,
		order_by=order_by,
		offset=start,
		limit=page_length or None,
		distinct=distinct,
		ignore_permissions=True,
	)
	if not is_course_staff():
		course = frappe.qb.DocType("LMS Course")
		enrollment = frappe.qb.DocType("LMS Enrollment")
		instructor = frappe.qb.DocType("Course Instructor")
		user = frappe.session.user
		query = query.where(
			((course.is_public == 1) & (course.published == 1))
			| course.name.isin(
				frappe.qb.from_(enrollment).select(enrollment.course).where(enrollment.member == user)
			)
			| course.name.isin(
				frappe.qb.from_(instructor)
				.select(instructor.parent)
				.where((instructor.parenttype == "LMS Course") & (instructor.instructor == user))
			)
		)
	rows = query.run(as_dict=True)
	return [row[pluck] for row in rows] if pluck else rows
