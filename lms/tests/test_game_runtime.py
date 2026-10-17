import base64
import json
import secrets
import unittest
from unittest.mock import patch

import frappe

from lms.lms import game, game_runtime as runtime


class TestGameRuntime(unittest.TestCase):
	def setUp(self):
		frappe.set_user('Administrator')
		self.saved_sid = frappe.session.sid
		frappe.session.sid = secrets.token_hex(16)
		self.origin = 'http://localhost:2567'
		self.config = patch.dict(frappe.conf, {'game_runtime_allowed_origins': [self.origin], 'game_runtime_service_keys': {}})
		self.config.start()
		self.conf_reader = patch.object(runtime, '_runtime_config', return_value=frappe.conf)
		self.conf_reader.start()
		self.session = patch.object(runtime, 'session_is_active', return_value=True)
		self.session_mock = self.session.start()
		created = game.upload_game('runtime.html', base64.b64encode(b'<html>Runtime</html>').decode())
		self.game = created['name']
		manifest = {'rooms': [{'key': 'arena'}]}
		self.release = frappe.get_doc({'doctype': 'LMS Game Release', 'game': self.game, 'version': '1.0.0', 'game_key': 'test', 'manifest': json.dumps(manifest), 'client_sha256': 'a' * 64, 'html_base64': base64.b64encode(b'<html>Release</html>').decode(), 'runtime_profile': 'colyseus-web-v1', 'server_image': 'test@sha256:' + 'b' * 64, 'status': 'Ready'}).insert(ignore_permissions=True)
		self.dep = frappe.get_doc({'doctype': 'LMS Game Deployment', 'release': self.release.name, 'endpoint': self.origin, 'status': 'Ready'}).insert(ignore_permissions=True)
		frappe.db.set_value('LMS Game', self.game, {'runtime_mode': 'Colyseus', 'active_release': self.release.name})
		frappe.conf.game_runtime_service_keys = {self.dep.name: 'k' * 64}
		self.headers = patch.object(frappe, 'get_request_header', side_effect=lambda name: {'X-Game-Deployment': self.dep.name, 'X-Game-Service-Key': 'k' * 64}.get(name))
		self.headers.start()

	def tearDown(self):
		frappe.session.sid = self.saved_sid
		self.headers.stop()
		self.session.stop()
		self.conf_reader.stop()
		self.config.stop()
		frappe.set_user('Administrator')
		frappe.db.rollback()
		frappe.clear_cache(doctype='LMS Settings')

	def ticket(self):
		launch = runtime.create_launch(self.game)
		return launch, runtime.issue_join_ticket(launch['launch_id'], 'arena')['ticket']

	def test_launch_uses_release_and_keeps_sid_private(self):
		launch = runtime.create_launch(self.game)
		self.assertEqual(launch['html'], '<html>Release</html>')
		self.assertEqual(launch['connect_sources'], [self.origin, 'ws://localhost:2567'])
		self.assertNotIn(frappe.session.sid, json.dumps(launch))
		self.assertEqual(game.get_game(self.game)['runtime_mode'], 'Colyseus')
		self.assertEqual(game.download_game(self.game)['content'], self.release.html_base64)

	def test_ticket_is_atomic_single_use_and_lease_renews(self):
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'arena')
		self.assertEqual(claim['deployment'], self.dep.name)
		self.assertNotIn('@', claim['player_id'])
		with self.assertRaises(frappe.PermissionError):
			runtime.redeem_ticket(ticket, 'arena')
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [claim['lease_id']])
		runtime.close_launch(launch['launch_id'])
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])

	def test_wrong_room_does_not_consume_ticket(self):
		_, ticket = self.ticket()
		with self.assertRaises(frappe.PermissionError):
			runtime.redeem_ticket(ticket, 'other')
		self.assertTrue(runtime.redeem_ticket(ticket, 'arena')['lease_id'])

	def test_expired_and_malformed_tickets_rejected(self):
		_, ticket = self.ticket()
		frappe.cache.delete(runtime._key('ticket', ticket))
		for value in [ticket, 'invalid']:
			with self.assertRaises(frappe.PermissionError):
				runtime.redeem_ticket(value, 'arena')

	def test_invalid_service_identity_rejected(self):
		_, ticket = self.ticket()
		with patch.object(frappe, 'get_request_header', return_value='wrong'):
			with self.assertRaises(frappe.PermissionError):
				runtime.redeem_ticket(ticket, 'arena')
		self.assertTrue(runtime.redeem_ticket(ticket, 'arena'))

	def test_closed_session_revokes_active_lease_and_new_ticket(self):
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'arena')
		self.session_mock.return_value = False
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])
		with self.assertRaises(frappe.PermissionError):
			runtime.issue_join_ticket(launch['launch_id'], 'arena')

	def test_other_session_cannot_use_launch(self):
		launch = runtime.create_launch(self.game)
		frappe.session.sid = secrets.token_hex(16)
		for operation in [lambda: runtime.issue_join_ticket(launch['launch_id'], 'arena'), lambda: runtime.close_launch(launch['launch_id'])]:
			with self.assertRaises(frappe.PermissionError):
				operation()

	def test_drain_keeps_existing_lease_but_denies_new_matching(self):
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'arena')
		frappe.db.set_value('LMS Game Deployment', self.dep.name, 'status', 'Draining')
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [claim['lease_id']])
		with self.assertRaises(frappe.PermissionError):
			runtime.issue_join_ticket(launch['launch_id'], 'arena')
		frappe.db.set_value('LMS Game Deployment', self.dep.name, 'status', 'Stopped')
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])

	def test_student_revoked_while_teacher_can_preview(self):
		student = f'game-runtime-{secrets.token_hex(6)}@example.com'
		frappe.get_doc({'doctype': 'User', 'email': student, 'first_name': 'Runtime Test', 'send_welcome_email': 0, 'roles': [{'role': 'LMS Student'}]}).insert(ignore_permissions=True)
		game.set_game_enabled(1)
		frappe.db.set_single_value('LMS Settings', 'game_require_course_completion', 0)
		frappe.set_user(student)
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'arena')
		frappe.set_user('Administrator')
		game.set_game_availability(self.game, 0)
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])
		self.assertTrue(runtime.create_launch(self.game))

	def test_unapproved_origin_and_foreign_release_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			runtime.validate_endpoint('https://evil.example')
		with self.assertRaises(frappe.PermissionError):
			runtime.connection_sources('not-this-game', self.release.name)


def prepare_browser_smoke(game_name):
	"""Explicit local QA fixture; not exposed over HTTP."""
	frappe.only_for('System Manager')
	from frappe.utils.password import update_password
	from lms.lms.game_access import get_game_access
	accounts = []
	for index in range(2):
		user = f'colyseus-qa-{secrets.token_hex(6)}@example.com'
		password = secrets.token_urlsafe(24)
		frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': f'联机验收 {index + 1}', 'send_welcome_email': 0, 'roles': [{'role': 'LMS Student'}]}).insert(ignore_permissions=True)
		update_password(user, password)
		accounts.append({'user': user, 'password': password})
	original = frappe.db.get_value('LMS Game', game_name, 'enabled')
	# Do not change global access policy for a browser test.
	for account in accounts:
		if not get_game_access(account['user'])['can_enter']:
			frappe.throw('Local students are locked; configure QA access before running smoke.')
	game.set_game_availability(game_name, 1)
	frappe.db.commit()
	return {'game': game_name, 'accounts': accounts, 'original_enabled': original}


def cleanup_browser_smoke(fixture):
	frappe.only_for('System Manager')
	for account in fixture['accounts']:
		if not account['user'].startswith('colyseus-qa-'):
			frappe.throw('Unexpected QA account.')
		frappe.delete_doc('User', account['user'], ignore_permissions=True, force=True)
	game.set_game_availability(fixture['game'], fixture['original_enabled'])
	frappe.db.commit()
	return {'cleaned': True}
