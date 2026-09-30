"""Validate game archives and serve their resources in an opaque browser origin."""

import base64
import binascii
import mimetypes
import secrets
import shutil
import stat
import zipfile
import zlib
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import frappe
from frappe import _
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response

MAX_ZIP_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_ASSET_BYTES = 20 * 1024 * 1024
MAX_FILES = 1000
TOKEN_TTL = 8 * 60 * 60


def validate_package(content):
	if not isinstance(content, str) or len(content) > 4 * ((MAX_ZIP_BYTES + 2) // 3):
		frappe.throw(_("ZIP game packages must be no larger than 20 MB."))
	try:
		raw = base64.b64decode(content, validate=True)
		if len(raw) > MAX_ZIP_BYTES:
			raise ValueError("ZIP game packages must be no larger than 20 MB.")
		files = {}
		seen = set()
		total = 0
		with zipfile.ZipFile(BytesIO(raw)) as archive:
			if len(archive.infolist()) > MAX_FILES:
				raise ValueError("ZIP game packages may contain at most 1000 entries.")
			for info in archive.infolist():
				path = info.filename
				parts = PurePosixPath(path).parts
				if not parts or str(PurePosixPath(path)) != path.rstrip('/') or path.startswith('/') or any(p in ('..', '.') for p in path.split('/')) or any(c in path for c in ('\\', ':', '\x00', '%', '?', '#')) or len(path) > 512:
					raise ValueError("The ZIP contains an invalid file path.")
				mode = info.external_attr >> 16
				if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)) or info.flag_bits & 1:
					raise ValueError("Encrypted files and links are not supported in game packages.")
				if info.is_dir() or parts[0] == '__MACOSX' or parts[-1] == '.DS_Store':
					continue
				if path.casefold() in seen:
					raise ValueError("The ZIP contains duplicate file paths.")
				seen.add(path.casefold())
				total += info.file_size
				if total > MAX_EXPANDED_BYTES or info.file_size > MAX_ASSET_BYTES:
					raise ValueError("The ZIP may expand to at most 100 MB, with each file at most 20 MB.")
				if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
					raise ValueError("Please use a standard ZIP archive (stored or deflated).")
				files[path] = archive.read(info)
		for path in files:
			if any(str(parent).casefold() in seen for parent in PurePosixPath(path).parents if str(parent) != '.'):
				raise ValueError('The ZIP contains conflicting file and directory paths.')
		entry = find_entry(files)
		from lms.lms.game import _HTMLDetector
		html = files[entry].decode('utf-8-sig')
		parser = _HTMLDetector()
		parser.feed(html)
		if not parser.has_html or '\x00' in html:
			raise ValueError("The ZIP entry must contain valid UTF-8 HTML.")
		return base64.b64encode(raw).decode('ascii'), entry, files
	except (zipfile.BadZipFile, zlib.error, binascii.Error, UnicodeDecodeError, RuntimeError, NotImplementedError, ValueError) as exc:
		frappe.throw(_("Invalid ZIP game package: {0}").format(str(exc)))


def find_entry(files):
	html = [path for path in files if PurePosixPath(path).suffix.lower() in ('.html', '.htm')]
	indexes = [path for path in html if PurePosixPath(path).name.lower() in ('index.html', 'index.htm')]
	if indexes:
		depth = min(len(PurePosixPath(path).parts) for path in indexes)
		indexes = [path for path in indexes if len(PurePosixPath(path).parts) == depth]
		if len(indexes) == 1:
			return indexes[0]
	if len(html) == 1:
		return html[0]
	raise ValueError("Place one index.html at the root of the ZIP, or include a single HTML entry file.")


def package_root(name):
	root = Path(frappe.get_site_path('private', 'lms-game-packages')).resolve()
	path = (root / name).resolve()
	if path.parent != root:
		raise frappe.PermissionError
	return path


def store_package(name, files):
	root = package_root(name)
	root.mkdir(parents=True, exist_ok=False)
	# A database rollback must not leave unpacked game files behind.
	frappe.db.after_rollback.add(lambda: shutil.rmtree(root, ignore_errors=True))
	try:
		for path, content in files.items():
			target = (root / path).resolve()
			if not target.is_relative_to(root):
				raise frappe.PermissionError
			target.parent.mkdir(parents=True, exist_ok=True)
			target.write_bytes(content)
	except Exception:
		shutil.rmtree(root, ignore_errors=True)
		raise


def remove_package_after_commit(name):
	root = package_root(name)
	frappe.db.after_commit.add(lambda: shutil.rmtree(root, ignore_errors=True))


def launch_url(game):
	token = secrets.token_hex(32)
	frappe.cache.set_value('game-package:' + token, {'game': game.name, 'user': frappe.session.user}, expires_in_sec=TOKEN_TTL)
	return '/game-assets/' + token + '/' + quote(game.entry_file, safe='/')


class GamePackageRenderer(BaseRenderer):
	def can_render(self):
		return self.path.startswith('game-assets/')

	def render(self):
		from lms.lms.game import game_visible
		# Frappe's page resolver removes .html; packaged assets need the exact
		# original request path for relative URLs and filenames to keep working.
		request_path = getattr(getattr(frappe.local, 'request', None), 'path', self.path)
		parts = request_path.lstrip('/').split('/', 2)
		if len(parts) != 3 or len(parts[1]) != 64 or any(c not in '0123456789abcdef' for c in parts[1]):
			raise frappe.PermissionError
		token, resource = parts[1:]
		access = frappe.cache.get_value('game-package:' + token)
		if not access or not frappe.db.get_value('User', access['user'], 'enabled') or not game_visible(access['user']):
			raise frappe.PermissionError
		if not frappe.db.exists('LMS Game', access['game']):
			raise frappe.DoesNotExistError
		root = package_root(access['game'])
		path = (root / resource).resolve()
		if not path.is_relative_to(root) or not path.is_file():
			raise frappe.DoesNotExistError
		mime = {'.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm'}.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
		response = Response(path.read_bytes(), mimetype=mime)
		# Authorization travels in the unguessable URL: opaque iframe origins
		# cannot depend on same-site cookies for scripts, modules or fetch calls.
		asset_root = frappe.local.request.host_url.rstrip('/') + '/game-assets/' + token + '/'
		policy = f"sandbox allow-scripts allow-pointer-lock; default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' {asset_root} https: blob:; style-src 'unsafe-inline' {asset_root} https:; img-src {asset_root} https: data: blob:; media-src {asset_root} https: data: blob:; font-src {asset_root} https: data:; connect-src {asset_root}; frame-src {asset_root}; worker-src blob:; base-uri 'none'; form-action 'none'"
		response.headers.update({
			'Content-Security-Policy': policy,
			'Access-Control-Allow-Origin': '*',
			'Cross-Origin-Resource-Policy': 'cross-origin',
			'Referrer-Policy': 'no-referrer',
			'X-Content-Type-Options': 'nosniff',
			'Cache-Control': 'no-store',
		})
		return response
