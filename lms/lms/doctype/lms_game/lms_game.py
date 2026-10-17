import frappe
from frappe.model.document import Document


class LMSGame(Document):
	def on_trash(self):
		# Releases and deployments are owned by this logical game.
		self.active_release = None
		frappe.db.set_value("LMS Game", self.name, "active_release", None)
		for release in frappe.get_all("LMS Game Release", filters={"game": self.name}, pluck="name"):
			for deployment in frappe.get_all("LMS Game Deployment", filters={"release": release}, pluck="name"):
				frappe.delete_doc("LMS Game Deployment", deployment, ignore_permissions=True)
			frappe.delete_doc("LMS Game Release", release, ignore_permissions=True)
		if self.entry_file:
			from lms.lms.game_package import remove_package_after_commit
			remove_package_after_commit(self.name)
