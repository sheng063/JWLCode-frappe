import frappe
from frappe.model.document import Document
from lms.lms.game_access import MODES, require_student_scope, notify_access_change, validate_unlock_target


class LMSGameStudentAccess(Document):
	def validate(self):
		require_student_scope(self.student, self.required_course)
		validate_unlock_target(self.required_course, self.required_lesson)
		before = self.get_doc_before_save()
		if before and before.student != self.student:
			frappe.throw("学生账号不能修改。")
		if self.access_mode not in MODES or len(self.reason or "") > 500:
			frappe.throw("访问模式无效或原因超过 500 字。")

	def on_update(self):
		notify_access_change(self)

	def on_trash(self):
		require_student_scope(self.student)
		notify_access_change(self)
