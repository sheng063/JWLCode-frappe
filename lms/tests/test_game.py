import base64
import unittest
from unittest.mock import patch

import frappe

from lms.lms import game
from lms.lms.api import get_sidebar_settings


class TestGame(unittest.TestCase):
	def setUp(self):
		frappe.set_user('Administrator')
		self.teacher = self.make_user('Course Creator')
		self.student = self.make_user('LMS Student')
		frappe.db.set_single_value("LMS Settings", "game_require_course_completion", 0)
		game.set_game_enabled(0)
		self.html = '<!doctype html><html><body>游戏<script>window.score=1</script></body></html>'
		self.content = base64.b64encode(self.html.encode()).decode()

	def tearDown(self):
		frappe.set_user('Administrator')
		frappe.db.rollback()
		frappe.clear_cache(doctype='LMS Settings')

	def make_user(self, role):
		name = f'game-qa-{frappe.generate_hash(length=10)}@example.com'
		frappe.get_doc(dict(doctype='User', email=name, first_name='Game QA', send_welcome_email=0,
			roles=[dict(role=role)])).insert(ignore_permissions=True)
		return name

	def test_teacher_upload_roundtrip_and_sidebar(self):
		frappe.set_user(self.teacher)
		created = game.upload_game('demo.HTML', self.content, '小游戏')
		self.assertEqual(game.get_game(created['name'])['html'], self.html)
		self.assertIn(created['name'], [item.name for item in game.get_games()])
		self.assertEqual(get_sidebar_settings().game, 1)
		self.assertFalse(game.get_game_settings()['enabled'])
		with patch.object(frappe, 'publish_realtime') as publish:
			self.assertTrue(game.set_game_enabled(1)['enabled'])
			publish.assert_called_once_with('lms_game_visibility_changed', room='website', after_commit=True)

	def test_student_access_follows_switch_and_no_generic_rest_read(self):
		created = game.upload_game('game.html', self.content)
		frappe.set_user(self.student)
		self.assertEqual(get_sidebar_settings().game, 0)
		for action in (game.get_games, lambda: game.get_game(created['name']),
			lambda: game.upload_game('game.html', self.content), lambda: game.set_game_enabled(1)):
			with self.assertRaises(frappe.PermissionError):
				action()
		frappe.set_user(self.teacher)
		game.set_game_enabled(1)
		frappe.set_user(self.student)
		self.assertEqual(get_sidebar_settings().game, 1)
		self.assertEqual(game.get_game(created['name'])['html'], self.html)
		self.assertFalse(frappe.has_permission('LMS Game', 'read'))
		frappe.set_user(self.teacher)
		game.set_game_enabled(0)
		frappe.set_user(self.student)
		with self.assertRaises(frappe.PermissionError):
			game.get_game(created['name'])

	def test_guest_cannot_access_even_when_enabled(self):
		game.set_game_enabled(1)
		frappe.set_user('Guest')
		self.assertFalse(game.game_visible())
		for action in (game.get_games, lambda: game.upload_game('game.html', self.content), lambda: game.set_game_enabled(0)):
			with self.assertRaises(frappe.PermissionError):
				action()

	def test_upload_validation(self):
		for filename, content in [('game.exe', self.content), ('game.html', ''), ('game.html', '!bad'),
			('game.html', base64.b64encode(b'plain text').decode()),
			('game.html', base64.b64encode(b'\xff\xfe').decode())]:
			with self.subTest(filename=filename, content=content):
				with self.assertRaises(frappe.ValidationError):
					game.upload_game(filename, content)
		with patch.object(game, 'MAX_GAME_BYTES', 10):
			with self.assertRaises(frappe.ValidationError):
				game.upload_game('game.html', self.content)
		# Frappe validates the annotated argument before entering the handler.
		from frappe.exceptions import FrappeTypeError
		with self.assertRaises((frappe.ValidationError, FrappeTypeError)):
			game.set_game_enabled('invalid')

	def test_teacher_edits_cover_downloads_and_deletes(self):
		from io import BytesIO
		from PIL import Image
		frappe.set_user(self.teacher)
		created = game.upload_game('game.html', self.content)
		image = BytesIO()
		Image.new('RGB', (120, 80), 'blue').save(image, format='PNG')
		cover = base64.b64encode(image.getvalue()).decode()
		updated = game.update_game(created['name'], 'New title', 'How to play', cover)
		self.assertTrue(updated['cover_image'].startswith('data:image/jpeg;base64,'))
		self.assertEqual(updated['description'], 'How to play')
		self.assertEqual(game.update_game(created['name'], 'Renamed')['cover_image'], updated['cover_image'])
		listing = next(g for g in game.get_games() if g.name == created['name'])
		self.assertEqual(listing.title, 'Renamed')
		self.assertEqual(listing.cover_image, updated['cover_image'])
		download = game.download_game(created['name'])
		self.assertEqual(download['filename'], 'game.html')
		self.assertEqual(base64.b64decode(download['content']).decode(), self.html)
		self.assertEqual(game.update_game(created['name'], 'Renamed', cover='')['cover_image'], '')
		game.delete_game(created['name'])
		self.assertFalse(frappe.db.exists('LMS Game', created['name']))
		with self.assertRaises(frappe.DoesNotExistError):
			game.get_game(created['name'])

	def test_students_and_guests_cannot_manage_games(self):
		created = game.upload_game('game.html', self.content)
		game.set_game_enabled(1)
		for user in [self.student, 'Guest']:
			frappe.set_user(user)
			for action in [lambda: game.update_game(created['name'], 'Changed'),
				lambda: game.download_game(created['name']), lambda: game.delete_game(created['name'])]:
				with self.assertRaises(frappe.PermissionError):
					action()

	def test_invalid_metadata_and_cover_do_not_change_game(self):
		created = game.upload_game('game.html', self.content)
		for args in [dict(title=' '), dict(title='x'*141), dict(title='New', description='x'*501),
			dict(title='New', cover='invalid'), dict(title='New', cover=base64.b64encode(b'<svg/>').decode()),
			dict(title='New', cover='A'*(4*((game.MAX_COVER_BYTES+2)//3)+1))]:
			with self.assertRaises(frappe.ValidationError):
				game.update_game(created['name'], **args)
		self.assertEqual(frappe.db.get_value('LMS Game',created['name'],'title'), 'game')

	def test_individual_game_switch_is_independent_and_enforced(self):
		frappe.set_user(self.teacher)
		first = game.upload_game('first.html', self.content)['name']
		second = game.upload_game('second.html', self.content)['name']
		game.set_game_enabled(1)
		with patch.object(frappe, 'publish_realtime') as publish:
			self.assertFalse(game.set_game_availability(first, 0)['enabled'])
			publish.assert_any_call('lms_game_visibility_changed', room='website', after_commit=True)
		self.assertTrue(game.get_game_settings()['enabled'])
		self.assertIn(first, [item.name for item in game.get_games()])
		self.assertEqual(game.get_game(first)['html'], self.html)
		frappe.set_user(self.student)
		self.assertFalse(game.get_game_settings(first)['game_enabled'])
		self.assertTrue(game.get_game_settings(second)['game_enabled'])
		self.assertNotIn(first, [item.name for item in game.get_games()])
		self.assertIn(second, [item.name for item in game.get_games()])
		with self.assertRaises(frappe.PermissionError):
			game.get_game(first)
		self.assertEqual(game.get_game(second)['html'], self.html)
		for user in (self.student, 'Guest'):
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError):
				game.set_game_availability(first, 1)
		frappe.set_user(self.teacher)
		with self.assertRaises(frappe.ValidationError):
			game.set_game_availability(first, 2)
		self.assertFalse(frappe.db.get_value('LMS Game', first, 'enabled'))
		game.set_game_availability(first, 1)
		frappe.set_user(self.student)
		self.assertEqual(game.get_game(first)['html'], self.html)
		frappe.set_user(self.teacher)
		game.set_game_enabled(0)
		frappe.set_user(self.student)
		with self.assertRaises(frappe.PermissionError):
			game.get_game(first)
