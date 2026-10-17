import frappe
from frappe.model.document import Document


class LMSGameRelease(Document):
	def validate(self):
		before = self.get_doc_before_save()
		if not before:
			return
		immutable = ('game', 'game_key', 'version', 'manifest', 'client_sha256', 'html_base64', 'entry_file', 'filename', 'client_type', 'platform_api', 'compatibility_key')
		if any(self.get(field) != before.get(field) for field in immutable):
			frappe.throw('已发布的游戏资源和协议不能原地修改，请发布新版本。')
