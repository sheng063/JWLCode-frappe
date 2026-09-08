import frappe
from frappe.model.document import Document

from lms.lms.problem_package.permissions import INTERNAL_WRITE


class LMSProgrammingExerciseSubmission(Document):
	def validate(self):
		old = self.get_doc_before_save()
		package = self.package_version or (old and old.package_version)
		active = frappe.db.get_value("LMS Programming Exercise", self.exercise, "active_package_version")
		if (package or active) and self.flags.package_service is not INTERNAL_WRITE:
			frappe.throw("Package attempts can only be saved by Judge Service.")

	def on_update(self):
		old = self.get_doc_before_save()
		if self.status == "Passed" and (not old or old.status != "Passed"):
			frappe.enqueue(
				complete_programming_lessons,
				exercise=self.exercise,
				member=self.member,
				enqueue_after_commit=True,
			)


def complete_programming_lessons(exercise, member):
	"""Credit passing submissions even when the student has left the lesson."""
	from lms.lms.doctype.course_lesson.course_lesson import save_progress
	from lms.lms.permissions import get_locked_lessons
	from lms.lms.utils import get_editorjs_blocks

	courses = frappe.get_all("LMS Enrollment", filters={"member": member}, pluck="course")
	if not courses:
		return
	previous_user = frappe.session.user
	try:
		frappe.set_user(member)
		for lesson in frappe.get_all(
			"Course Lesson", filters={"course": ["in", courses]}, fields=["name", "course", "content"]
		):
			if not any(
				block.get("type") == "program" and (block.get("data") or {}).get("exercise") == exercise
				for block in get_editorjs_blocks(lesson.content)
			):
				continue
			if lesson.name not in get_locked_lessons(lesson.course):
				save_progress(lesson.name, lesson.course)
	finally:
		frappe.set_user(previous_user)
