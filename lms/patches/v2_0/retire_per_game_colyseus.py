"""Preserve legacy artifacts, disable incompatible per-game server releases."""
import frappe


def execute():
	if not frappe.db.table_exists('LMS Game Release'):
		return
	for game in frappe.get_all('LMS Game', filters={'runtime_mode': 'Colyseus'}, fields=['name', 'active_release']):
		# The old client protocol needs a replacement front-end release. Do not relabel it as relay.
		frappe.db.set_value('LMS Game', game.name, {'runtime_mode': 'Static', 'enabled': 0, 'active_release': None})
		frappe.db.set_value('LMS Game Release', {'game': game.name}, 'status', 'Retired')
	if frappe.db.table_exists('LMS Game Deployment'):
		frappe.db.sql("update `tabLMS Game Deployment` set status='Stopped'")
