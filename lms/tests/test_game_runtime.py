import base64
import json
import secrets
import unittest
from io import BytesIO
from unittest.mock import patch
import zipfile

import frappe

from lms.lms import game, game_runtime as runtime
from lms.lms.game_publish import publish_content, validate_manifest


def make_manifest(key, version='1.0.0', client_type='html', entry='relay.html', compatibility=None):
	mp = {'enabled': True, 'mode': 'relay', 'minPlayers': 2, 'maxPlayers': 4, 'allowPrivateRoom': True, 'allowQuickMatch': True}
	if compatibility:
		mp['compatibilityKey'] = compatibility
	return {'manifestVersion': 1, 'gameKey': key, 'release': version, 'platformApi': '1', 'client': {'entry': entry, 'type': client_type}, 'multiplayer': mp}


class TestGameRuntime(unittest.TestCase):
	def setUp(self):
		frappe.set_user('Administrator')
		self.saved_sid = frappe.session.sid
		frappe.session.sid = secrets.token_hex(16)
		self.origin = 'http://localhost:2572'
		self.config = patch.dict(frappe.conf, {'game_universal_runtime': {'endpoint': self.origin, 'service_key': 'k' * 64, 'status': 'Ready', 'protocolVersion': 1}})
		self.config.start()
		self.reader = patch.object(runtime, '_runtime_config', return_value=frappe.conf)
		self.reader.start()
		self.session = patch.object(runtime, 'session_is_active', return_value=True)
		self.session_mock = self.session.start()
		self.rate = patch.object(runtime, '_rate_limit')
		self.rate.start()
		self.headers = patch.object(frappe, 'get_request_header', side_effect=lambda key: {'X-Game-Runtime': 'universal', 'X-Game-Service-Key': 'k' * 64}.get(key))
		self.headers.start()
		self.key = 'relay-' + secrets.token_hex(6)
		self.content = base64.b64encode(b'<html>Universal relay</html>').decode()
		self.manifest = make_manifest(self.key)
		self.created = publish_content('relay.html', self.content, manifest=self.manifest)
		self.game = self.created['name']
		self.release = frappe.get_doc('LMS Game Release', self.created['release'])

	def tearDown(self):
		frappe.session.sid = self.saved_sid
		self.headers.stop()
		self.rate.stop()
		self.session.stop()
		self.reader.stop()
		self.config.stop()
		frappe.set_user('Administrator')
		frappe.db.rollback()
		frappe.clear_cache(doctype='LMS Settings')

	def ticket(self, action='quickMatch', **options):
		launch = runtime.create_launch(self.game)
		return launch, runtime.issue_join_ticket(launch['launch_id'], action, **options)['ticket']

	def test_launch_uses_release_and_never_exposes_sid(self):
		launch = runtime.create_launch(self.game)
		self.assertEqual(launch['html'], '<html>Universal relay</html>')
		self.assertEqual(launch['connect_sources'], [self.origin, 'ws://localhost:2572'])
		self.assertEqual(launch['multiplayer']['compatibilityKey'], '1.0.0')
		self.assertNotIn(frappe.session.sid, json.dumps(launch))
		self.assertEqual(game.get_game(self.game)['runtime_mode'], 'UniversalRelay')
		self.assertEqual(game.download_game(self.game)['content'], self.content)

	def test_single_use_ticket_and_online_lease(self):
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'quickMatch')
		self.assertEqual(claim['game_key'], self.key)
		self.assertEqual(claim['visibility'], 'public')
		self.assertNotIn('@', claim['player_id'])
		with self.assertRaises(frappe.PermissionError):
			runtime.redeem_ticket(ticket, 'quickMatch')
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [claim['lease_id']])
		runtime.close_launch(launch['launch_id'])
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])

	def test_ticket_binds_action_and_target_before_atomic_consumption(self):
		_, ticket = self.ticket('joinRoom', room_id='ABC12345')
		for action, target in [('createRoom', ''), ('joinRoom', 'ABC12346')]:
			with self.assertRaises(frappe.PermissionError):
				runtime.redeem_ticket(ticket, action, target)
		self.assertEqual(runtime.redeem_ticket(ticket, 'joinRoom', 'ABC12345')['room_id'], 'ABC12345')

	def test_expired_ticket_and_wrong_service_are_rejected(self):
		_, ticket = self.ticket()
		with patch.object(frappe, 'get_request_header', return_value='wrong'):
			with self.assertRaises(frappe.PermissionError):
				runtime.redeem_ticket(ticket, 'quickMatch')
		frappe.cache.delete(runtime._key('ticket', ticket))
		for value in [ticket, 'invalid']:
			with self.assertRaises(frappe.PermissionError):
				runtime.redeem_ticket(value, 'quickMatch')

	def test_closed_session_and_other_browser_cannot_authorize(self):
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'quickMatch')
		self.session_mock.return_value = False
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])
		with self.assertRaises(frappe.PermissionError):
			runtime.issue_join_ticket(launch['launch_id'], 'quickMatch')
		frappe.session.sid = secrets.token_hex(16)
		with self.assertRaises(frappe.PermissionError):
			runtime.close_launch(launch['launch_id'])

	def test_fixed_runtime_drain_and_stop(self):
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'quickMatch')
		frappe.conf.game_universal_runtime['status'] = 'Draining'
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [claim['lease_id']])
		with self.assertRaises(frappe.ValidationError):
			runtime.issue_join_ticket(launch['launch_id'], 'quickMatch')
		frappe.conf.game_universal_runtime['status'] = 'Stopped'
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])

	def test_new_game_and_upgrade_create_no_deployments(self):
		before = frappe.db.count('LMS Game Deployment')
		old_launch = runtime.create_launch(self.game)
		result = publish_content('relay.html', self.content, manifest=make_manifest(self.key, '2.0.0'), game=self.game)
		self.assertEqual(frappe.db.count('LMS Game Deployment'), before)
		self.assertNotEqual(result['release'], self.release.name)
		self.assertEqual(runtime._get('launch', old_launch['launch_id'])['release'], self.release.name)
		self.assertTrue(runtime.issue_join_ticket(old_launch['launch_id'], 'quickMatch'))
		self.assertEqual(runtime.create_launch(self.game)['multiplayer']['compatibilityKey'], '2.0.0')

	def test_explicit_compatible_releases_can_share_group(self):
		result = publish_content('relay.html', self.content, manifest=make_manifest(self.key, '2.0.0', compatibility='1.0.0'), game=self.game)
		self.assertEqual(frappe.db.get_value('LMS Game Release', result['release'], 'compatibility_key'), '1.0.0')

	def test_cross_game_key_duplicate_release_and_server_manifest_rejected(self):
		for manifest in [self.manifest, make_manifest('foreign-game', '2.0.0'), {**make_manifest(self.key, '2.0.0'), 'server': {'image': 'unwanted'}}]:
			with self.assertRaises(frappe.ValidationError):
				publish_content('relay.html', self.content, manifest=manifest, game=self.game)
		for key, value in [('platformApi','2'), ('runtimeProfile','colyseus-web-v1')]:
			manifest = make_manifest('valid-' + secrets.token_hex(3))
			manifest[key] = value
			with self.assertRaises(frappe.ValidationError):
				validate_manifest(manifest)

	def test_released_resources_are_immutable(self):
		self.release.html_base64 = base64.b64encode(b'<html>changed</html>').decode()
		with self.assertRaises(frappe.ValidationError):
			self.release.save(ignore_permissions=True)

	def test_room_permissions_and_limits_come_from_manifest(self):
		launch = runtime.create_launch(self.game)
		for action, options in [('quickMatch', {'max_players': 9}), ('createRoom', {'max_players': 1}), ('joinRoom', {'room_id': 'invalid!!!'}), ('other', {})]:
			with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
				runtime.issue_join_ticket(launch['launch_id'], action, **options)
		mp = json.loads(self.release.manifest)['multiplayer']
		mp['allowPrivateRoom'] = False
		manifest = make_manifest(self.key, '2.0.0')
		manifest['multiplayer'] = mp
		publish_content('relay.html', self.content, manifest=manifest, game=self.game)
		launch = runtime.create_launch(self.game)
		with self.assertRaises(frappe.PermissionError):
			runtime.issue_join_ticket(launch['launch_id'], 'createRoom')

	def test_upload_generates_front_end_manifest(self):
		result = game.upload_game('front.html', self.content, multiplayer={'enabled': True, 'release': '1.0.0', 'maxPlayers': 8, 'minPlayers': 2})
		release = frappe.get_doc('LMS Game Release', result['release'])
		self.assertEqual(release.client_type, 'html')
		self.assertEqual(json.loads(release.manifest)['multiplayer']['maxPlayers'], 8)
		self.assertEqual(frappe.db.get_value('LMS Game', result['name'], 'enabled'), 0)

	def test_zip_embedded_manifest_and_server_files(self):
		def package(extra=None):
			stream = BytesIO()
			with zipfile.ZipFile(stream, 'w') as archive:
				archive.writestr('index.html', '<html>ZIP</html>')
				archive.writestr('game.manifest.json', json.dumps(make_manifest('zip-' + secrets.token_hex(5), client_type='zip', entry='index.html')))
				if extra:
					archive.writestr(extra, 'not accepted')
			return base64.b64encode(stream.getvalue()).decode()
		result = game.upload_game('game.zip', package())
		self.assertEqual(result['runtime_mode'], 'UniversalRelay')
		# Wrapped ZIP roots must continue to work with a relative entry in the manifest.
		wrapped = BytesIO()
		with zipfile.ZipFile(wrapped, 'w') as archive:
			archive.writestr('outer/index.html', '<html>wrapped</html>')
			archive.writestr('outer/game.manifest.json', json.dumps(make_manifest('wrapped-' + secrets.token_hex(5), client_type='zip', entry='index.html')))
		result = game.upload_game('wrapped.zip', base64.b64encode(wrapped.getvalue()).decode())
		self.assertEqual(frappe.db.get_value('LMS Game Release', result['release'], 'entry_file'), 'outer/index.html')
		for filename in ['server/index.js', 'Dockerfile', 'package.json']:
			with self.assertRaises(frappe.ValidationError):
				game.upload_game('game.zip', package(filename))

	def test_students_cannot_publish_and_disabled_students_lose_lease(self):
		student = f'game-relay-{secrets.token_hex(6)}@example.com'
		frappe.get_doc({'doctype': 'User', 'email': student, 'first_name': 'Relay Test', 'send_welcome_email': 0, 'roles': [{'role': 'LMS Student'}]}).insert(ignore_permissions=True)
		game.set_game_enabled(1)
		game.set_game_availability(self.game, 1)
		frappe.db.set_single_value('LMS Settings', 'game_require_course_completion', 0)
		frappe.set_user(student)
		with self.assertRaises(frappe.PermissionError):
			publish_content('relay.html', self.content, manifest=make_manifest('not-allowed'))
		launch, ticket = self.ticket()
		claim = runtime.redeem_ticket(ticket, 'quickMatch')
		frappe.set_user('Administrator')
		game.set_game_availability(self.game, 0)
		self.assertEqual(runtime.renew_leases([claim['lease_id']])['valid'], [])
		self.assertTrue(runtime.create_launch(self.game))

	def test_csp_uses_fixed_service_only_and_rejects_foreign_release(self):
		with self.assertRaises(frappe.PermissionError):
			runtime.connection_sources('foreign', self.release.name)
		for url in ['http://external.example', 'https://example.test;script-src*', 'https://a.test/path']:
			with self.assertRaises(frappe.ValidationError):
				runtime.validate_endpoint(url)


# Trusted local browser QA helpers; never exposed over HTTP.
def prepare_browser_smoke(game_name, count=2, extra_games=None):
	frappe.only_for('System Manager')
	from frappe.utils.password import update_password
	from lms.lms.game_access import get_game_access
	accounts = []
	for index in range(count):
		user = f'colyseus-qa-{secrets.token_hex(6)}@example.com'
		password = secrets.token_urlsafe(24)
		frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': f'联机验收 {index + 1}', 'send_welcome_email': 0, 'roles': [{'role': 'LMS Student'}]}).insert(ignore_permissions=True)
		update_password(user, password)
		if not get_game_access(user)['can_enter']:
			frappe.throw('Local policy does not allow QA students. Global access policy was not changed.')
		accounts.append({'user': user, 'password': password})
	games = {name: frappe.db.get_value('LMS Game', name, 'enabled') for name in [game_name, *(extra_games or [])]}
	for name in games:
		game.set_game_availability(name, 1)
	frappe.db.commit()
	return {'game': game_name, 'accounts': accounts, 'games': games}


def cleanup_browser_smoke(fixture):
	frappe.only_for('System Manager')
	for account in fixture['accounts']:
		if not account['user'].startswith('colyseus-qa-'):
			frappe.throw('Unexpected QA account.')
		frappe.delete_doc('User', account['user'], ignore_permissions=True, force=True)
	for name, enabled in fixture['games'].items():
		game.set_game_availability(name, enabled)
	frappe.db.commit()
	return {'cleaned': True}
