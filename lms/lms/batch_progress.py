"""Batch-wide progress for the visible page of students."""

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_student_progress(batch: str, members: str | list):
	from lms.lms.utils import can_modify_batch, get_editorjs_blocks

	if not can_modify_batch(batch):
		frappe.throw(_("You do not have permission to view this batch's progress."), frappe.PermissionError)
	members = frappe.parse_json(members) if isinstance(members, str) else members
	if not isinstance(members, list) or len(members) > 500:
		frappe.throw(_("Select at most 500 students."))
	members = frappe.get_all(
		"LMS Batch Enrollment", filters={"batch": batch, "member": ["in", members]}, pluck="member"
	)
	courses = sorted(
		set(
			frappe.get_all(
				"Batch Course", filters={"parent": batch, "parenttype": "LMS Batch"}, pluck="course"
			)
		)
	)
	result = {member: {"course_progress": 0, "programming_pass_rate": 0} for member in members}
	if not courses or not members:
		return result
	for enrollment in frappe.get_all(
		"LMS Enrollment",
		filters={"course": ["in", courses], "member": ["in", members]},
		fields=["member", "progress"],
	):
		result[enrollment.member]["course_progress"] += flt(enrollment.progress) / len(courses)
	exercises = set()
	for lesson in frappe.get_all("Course Lesson", filters={"course": ["in", courses]}, fields=["content"]):
		for block in get_editorjs_blocks(lesson.content):
			if block.get("type") == "program":
				exercise = (block.get("data") or {}).get("exercise")
				if exercise:
					exercises.add(exercise)
	if exercises:
		passed = {member: set() for member in members}
		for submission in frappe.get_all(
			"LMS Programming Exercise Submission",
			filters={"member": ["in", members], "exercise": ["in", sorted(exercises)], "status": "Passed"},
			fields=["member", "exercise"],
			distinct=True,
		):
			passed[submission.member].add(submission.exercise)
		for member in members:
			result[member]["programming_pass_rate"] = len(passed[member]) * 100 / len(exercises)
	for values in result.values():
		for key in values:
			values[key] = round(values[key], 2)
	return result
