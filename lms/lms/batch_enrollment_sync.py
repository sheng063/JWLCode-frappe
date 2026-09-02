import frappe


def enroll_member_in_batch_course(batch: str, member: str, course: str):
	"""Create the course enrollment implied by a batch membership, if needed."""
	frappe.db.get_value("LMS Course", course, "name", for_update=True)
	if frappe.db.exists("LMS Enrollment", {"course": course, "member": member}):
		return
	enrollment = frappe.new_doc("LMS Enrollment")
	enrollment.course = course
	enrollment.member = member
	enrollment.enrollment_from_batch = batch
	enrollment.save()


def enroll_member_in_batch_courses(batch: str, member: str, courses: list[str] | None = None):
	"""Enroll a batch member in all supplied (or current) batch courses."""
	if courses is None:
		courses = frappe.get_all("Batch Course", {"parent": batch}, pluck="course")
	for course in courses:
		enroll_member_in_batch_course(batch, member, course)


def remove_member_from_batch_course(batch: str, member: str, course: str):
	"""Remove a batch-created enrollment, preserving an independent/other batch source."""
	frappe.db.get_value("LMS Course", course, "name", for_update=True)
	enrollment_name = frappe.db.exists(
		"LMS Enrollment", {"course": course, "member": member, "enrollment_from_batch": batch}
	)
	if not enrollment_name:
		return

	replacement_batch = _get_other_batch_for_member_course(batch, member, course)
	if replacement_batch:
		enrollment = frappe.get_doc("LMS Enrollment", enrollment_name)
		enrollment.enrollment_from_batch = replacement_batch
		enrollment.save(ignore_permissions=True)
		return

	frappe.delete_doc("LMS Enrollment", enrollment_name, ignore_permissions=True)


def remove_member_from_batch_courses(batch: str, member: str, courses: list[str] | None = None):
	"""Remove this batch's enrollment source for each supplied/current course."""
	if courses is None:
		courses = frappe.get_all("Batch Course", {"parent": batch}, pluck="course")
	for course in courses:
		remove_member_from_batch_course(batch, member, course)


def _get_other_batch_for_member_course(batch: str, member: str, course: str) -> str | None:
	"""Return another current batch that still makes the course available."""
	batches = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"member": member, "batch": ["!=", batch]},
		pluck="batch",
	)
	if not batches:
		return None
	return frappe.db.get_value(
		"Batch Course", {"parent": ["in", batches], "course": course}, "parent"
	)
