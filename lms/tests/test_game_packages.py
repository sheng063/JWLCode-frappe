import base64
import stat
import unittest
import zipfile
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.auth import CookieManager
from frappe.utils import now

from lms.lms import game, game_package as package


def make_zip(files):
	out = BytesIO()
	with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
		for path, content in files:
			archive.writestr(path, content)
	return base64.b64encode(out.getvalue()).decode()


class TestGamePackages(unittest.TestCase):
	def setUp(self):
		frappe.set_user('Administrator')
		frappe.db.set_single_value('LMS Settings', 'game_require_course_completion', 0)
		self.files = [('demo/index.html', '<html><script src="js/game.js"></script></html>'),
			('demo/js/game.js', 'window.score=42;'), ('demo/data/config.json', '{"score":42}')]
		self.archive = make_zip(self.files)
		self.paths = []
		self.tokens = []
		self.sid = frappe.generate_hash(length=32)
		frappe.session.sid = self.sid
		frappe.local.cookie_manager = CookieManager()
		data = {'user': 'Administrator', 'last_updated': now(), 'session_expiry': '240:00:00'}
		frappe.cache.hset('session', self.sid, {'user': 'Administrator', 'data': data})
		frappe.db.sql('insert into `tabSessions` (sid, user, sessiondata, lastupdate, status) values (%s, %s, %s, %s, %s)', (self.sid, 'Administrator', frappe.as_json(data), now(), 'Active'))

	def tearDown(self):
		frappe.set_user('Administrator')
		frappe.db.rollback()
		frappe.cache.hdel('session', self.sid)
		for path in self.paths:
			self.assertFalse(path.exists(), 'Rollback must remove extracted package files')
		for token in self.tokens:
			frappe.cache.delete_value('game-package:' + token)
		frappe.clear_cache(doctype='LMS Settings')

	def upload(self):
		created = game.upload_game('game.zip', self.archive)
		self.paths.append(package.package_root(created['name']))
		return created['name']

	def test_roundtrip_launch_assets_and_download(self):
		name = self.upload()
		result = game.get_game(name)
		self.assertNotIn('html', result)
		self.assertTrue(result['url'].endswith('/demo/index.html'))
		token = result['url'].split('/')[2]
		self.tokens.append(token)
		frappe.clear_cache()
		with patch.object(frappe.local, 'request', SimpleNamespace(host_url='http://localhost:8000/', cookies={'lms_game_session': frappe.cache.get_value('game-package:' + self.tokens[-1])['binding']}), create=True):
			frappe.local.request.path = f'/game-assets/{token}/demo/index.html'
			entry = package.GamePackageRenderer(path=f'game-assets/{token}/demo/index').render()
			self.assertIn(b'<html>', entry.get_data())
			del frappe.local.request.path
			response = package.GamePackageRenderer(path=f'game-assets/{token}/demo/js/game.js').render()
			self.assertEqual(response.get_data(), b'window.score=42;')
			self.assertEqual(response.mimetype, 'text/javascript')
			self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'null')
			self.assertEqual(response.headers['Access-Control-Allow-Credentials'], 'true')
			self.assertIn('sandbox allow-scripts allow-pointer-lock;', response.headers['Content-Security-Policy'])
			self.assertNotIn('allow-same-origin', response.headers['Content-Security-Policy'])
			with self.assertRaises(frappe.DoesNotExistError):
				package.GamePackageRenderer(path=f'game-assets/{token}/../../site_config.json').render()
		self.assertEqual(game.download_game(name)['content'], self.archive)

	def test_student_token_is_revoked_when_game_is_hidden(self):
		self.assert_student_token_revoked(individual=False)

	def test_student_token_is_revoked_when_individual_game_is_hidden(self):
		self.assert_student_token_revoked(individual=True)

	def assert_student_token_revoked(self, individual):
		name = self.upload()
		student = 'game-zip-' + frappe.generate_hash(length=10) + '@example.com'
		frappe.get_doc(dict(doctype='User',email=student,first_name='Zip QA',send_welcome_email=0,
			roles=[dict(role='LMS Student')])).insert(ignore_permissions=True)
		game.set_game_enabled(1)
		frappe.set_user(student)
		frappe.session.sid = self.sid
		frappe.cache.hset('session', self.sid, {'user': student, 'data': {'user': student, 'last_updated': now(), 'session_expiry': '240:00:00'}})
		url = game.get_game(name)['url']
		self.tokens.append(url.split('/')[2])
		frappe.set_user('Guest')
		# Opaque sandboxes send the dedicated HttpOnly cookie, not the LMS sid.
		with patch.object(frappe.local, 'request', SimpleNamespace(host_url='http://localhost:8000/', cookies={'lms_game_session': frappe.cache.get_value('game-package:' + self.tokens[-1])['binding']}), create=True):
			self.assertEqual(package.GamePackageRenderer(path=url).render().status_code, 200)
			frappe.local.request.cookies = {}
			with self.assertRaises(frappe.PermissionError):
				package.GamePackageRenderer(path=url).render()
			frappe.local.request.cookies = {'lms_game_session': 'other-browser'}
			with self.assertRaises(frappe.PermissionError):
				package.GamePackageRenderer(path=url).render()
		frappe.set_user('Administrator')
		if individual:
			game.set_game_availability(name, 0)
		else:
			game.set_game_enabled(0)
		with patch.object(frappe.local, 'request', SimpleNamespace(cookies={'lms_game_session': frappe.cache.get_value('game-package:' + self.tokens[-1])['binding']}), create=True):
			with self.assertRaises(frappe.PermissionError):
				package.GamePackageRenderer(path=url).render()

	def test_invalid_and_expired_tokens_are_rejected(self):
		with self.assertRaises(frappe.PermissionError):
			package.GamePackageRenderer(path='game-assets/' + '0'*64 + '/index.html').render()

	def test_zip_paths_entries_and_size_limits(self):
		bad_files = [
			[('../escape.html', '<html/>')], [('/index.html', '<html/>')], [('a\\index.html', '<html/>')],
			[('a//index.html', '<html/>')], [('index.html', '<html/>'), ('INDEX.HTML', '<html/>')],
			[('one.html', '<html/>'), ('two.html', '<html/>')], [('readme.txt', 'No entry')],
			[('index.html', '<html/>'), ('dir', 'x'), ('dir/a.js', 'x')],
		]
		for files in bad_files:
			with self.subTest(files=files), self.assertRaises(frappe.ValidationError):
				package.validate_package(make_zip(files))
		with self.assertRaises(frappe.ValidationError):
			package.validate_package('not a zip')
		with patch.object(package, 'MAX_EXPANDED_BYTES', 2), self.assertRaises(frappe.ValidationError):
			package.validate_package(self.archive)
		with patch.object(package, 'MAX_ZIP_BYTES', 2), self.assertRaises(frappe.ValidationError):
			package.validate_package(self.archive)
		info = zipfile.ZipInfo('index.html'); info.external_attr = (stat.S_IFLNK | 0o777) << 16
		with self.assertRaises(frappe.ValidationError):
			package.validate_package(make_zip([(info, '/etc/passwd')]))

	def test_single_html_and_root_index_selection(self):
		self.assertEqual(package.validate_package(make_zip([('game/play.htm', '<html/>')]))[1], 'game/play.htm')
		self.assertEqual(package.validate_package(make_zip([('index.html', '<html/>'), ('docs/index.html','<html/>')]))[1], 'index.html')

	def test_delete_schedules_filesystem_cleanup_after_commit(self):
		name = self.upload()
		root = package.package_root(name)
		with patch.object(frappe.db, 'after_commit') as after_commit:
			schedule = after_commit.add
			game.delete_game(name)
			self.assertTrue(root.exists())
			# Select the cleanup hook without committing the test transaction.
			callbacks = [args.args[0] for args in schedule.call_args_list]
			for callback in callbacks:
				callback()
		self.assertFalse(root.exists())

	def test_session_logout_and_expiry_revoke_assets(self):
		name = self.upload()
		url = game.get_game(name)['url']
		self.tokens.append(url.split('/')[2])
		binding = frappe.cache.get_value('game-package:' + self.tokens[-1])['binding']
		with patch.object(frappe.local, 'request', SimpleNamespace(host_url='http://localhost:8000/', cookies={'lms_game_session': binding}), create=True):
			self.assertEqual(package.GamePackageRenderer(path=url).render().status_code, 200)
			frappe.cache.hset('session', self.sid, {'user': 'Administrator', 'data': {'last_updated': '2000-01-01 00:00:00', 'session_expiry': '01:00:00'}})
			with self.assertRaises(frappe.PermissionError): package.GamePackageRenderer(path=url).render()
			frappe.cache.hdel('session', self.sid)
			frappe.db.sql('delete from `tabSessions` where sid=%s', self.sid)
			with self.assertRaises(frappe.PermissionError): package.GamePackageRenderer(path=url).render()

	def test_html_credentials_preserve_scripts_and_external_assets(self):
		raw = b'''<!doctype html><script type="module" src="./main.js"></script><script src="https://cdn.example/game.js"></script><script>const text='<script type="module" src="embedded.js">';</script>'''
		html = package.prepare_html(raw, 'http://localhost:8000/game-assets/token/').decode()
		self.assertTrue(html.startswith('<!doctype html>'))
		self.assertIn('<script type="module" src="./main.js" crossorigin="use-credentials">', html)
		self.assertIn('<script src="https://cdn.example/game.js">', html)
		self.assertIn("const text='<script type=\"module\" src=\"embedded.js\">';", html)

	def test_local_fonts_are_embedded_without_path_escape(self):
		name = self.upload()
		root = package.package_root(name)
		(root / 'font.woff2').write_bytes(b'font-data')
		result = package.prepare_css(b'@font-face{src:url("../font.woff2")} .x{background:url(pic.png)}', root / 'demo/style.css', root, 'http://localhost/game-assets/token/').decode()
		self.assertIn('base64,Zm9udC1kYXRh', result)
		self.assertIn('url(pic.png)', result)
