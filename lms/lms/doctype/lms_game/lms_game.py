from frappe.model.document import Document


class LMSGame(Document):
	def on_trash(self):
		if self.entry_file:
			from lms.lms.game_package import remove_package_after_commit
			remove_package_after_commit(self.name)
