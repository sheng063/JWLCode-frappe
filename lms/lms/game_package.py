"""Validate game archives and serve their resources in an opaque browser origin."""

import base64
import binascii
import mimetypes
import hashlib
import hmac
import re
from datetime import datetime, timezone
import secrets
import shutil
import stat
import zipfile
import zlib
from io import BytesIO
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit, unquote

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


def package_root(name, release=None):
	root = Path(frappe.get_site_path('private', 'lms-game-packages')).resolve()
	path = (root / name).resolve()
	if path.parent != root:
		raise frappe.PermissionError
	if release:
		if not re.fullmatch(r'[a-zA-Z0-9_-]+', release):
			raise frappe.PermissionError
		path = path / 'releases' / release
	return path


def store_package(name, files, release=None):
	root = package_root(name, release=release)
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


def session_is_active(sid, user):
	"""Check the original login, including logout and expiry, without changing session.user."""
	from frappe.sessions import get_expiry_in_seconds
	from frappe.utils import now_datetime, get_datetime
	if not sid or sid == 'Guest':
		return False
	cached = frappe.cache.hget('session', sid)
	if cached:
		owner, data = cached.get('user'), cached.get('data', {})
	else:
		row = frappe.db.get_value('Sessions', {'sid': sid}, ['user', 'sessiondata'], as_dict=True, order_by='sid')
		if not row:
			return False
		owner, data = row.user, frappe.parse_json(row.sessiondata or '{}')
	if owner != user or not data.get('last_updated'):
		return False
	if (now_datetime() - get_datetime(data['last_updated'])).total_seconds() > get_expiry_in_seconds(data.get('session_expiry')):
		return False
	end = data.get('session_end')
	return not end or datetime.now(timezone.utc) < datetime.fromisoformat(end)


def launch_url(game, release=None):
	request = getattr(frappe.local, 'request', None)
	if request and request.scheme != 'https' and request.host.split(':')[0] not in ('localhost', '127.0.0.1'):
		frappe.throw('ZIP 游戏的安全会话需要 HTTPS，请使用站点的 HTTPS 地址。')
	token = secrets.token_hex(32)
	sid = frappe.session.sid
	if not sid or sid == 'Guest':
		raise frappe.PermissionError
	# A separate HttpOnly cookie lets the opaque sandbox authenticate resources.
	# It cannot authenticate LMS API requests and exposes no login session secret.
	from frappe.utils.password import get_encryption_key
	binding = hmac.new(get_encryption_key().encode(), sid.encode(), hashlib.sha256).hexdigest()
	frappe.local.cookie_manager.set_cookie('lms_game_session', binding, secure=True, httponly=True, samesite='None', max_age=TOKEN_TTL)
	frappe.cache.set_value('game-package:' + token, {'game': game.name, 'user': frappe.session.user, 'sid': sid, 'binding': binding, 'release': release.name if release else None}, expires_in_sec=TOKEN_TTL)
	return '/game-assets/' + token + '/' + quote(release.entry_file if release else game.entry_file, safe='/')


def prepare_html(raw, asset_root):
	"""Keep relative asset URLs; credentialed requests carry the sandbox-only cookie."""
	import json
	html = raw.decode('utf-8-sig')
	# HTMLParser preserves script contents; regex over a whole document can
	# accidentally rewrite strings inside the game's JavaScript.
	class CredentialHTML(HTMLParser):
		def __init__(self):
			super().__init__(convert_charrefs=False)
			self.output = []

		def handle_starttag(self, tag, attrs):
			values = dict(attrs)
			text = self.get_starttag_text()
			source = values.get('src') or values.get('href') or ''
			local = not urlsplit(source).scheme and not urlsplit(source).netloc
			module = tag == 'script' and ((values.get('type') or '').lower() == 'module' or 'crossorigin' in values)
			preload = tag == 'link' and (values.get('rel') or '').lower() == 'modulepreload'
			if local and (module or preload):
				text = re.sub(r"\s+crossorigin(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?", '', text, flags=re.I)
				text = (text[:-2] + ' crossorigin="use-credentials" />') if text.endswith('/>') else (text[:-1] + ' crossorigin="use-credentials">')
			self.output.append(text)

		def handle_startendtag(self, tag, attrs):
			self.handle_starttag(tag, attrs)

		def handle_endtag(self, tag):
			self.output.append('</' + tag + '>')

		def handle_data(self, data):
			self.output.append(data)

		def handle_entityref(self, name):
			self.output.append('&' + name + ';')

		def handle_charref(self, name):
			self.output.append('&#' + name + ';')

		def handle_comment(self, data):
			self.output.append('<!--' + data + '-->')

		def handle_decl(self, decl):
			self.output.append('<!' + decl + '>')

		def handle_pi(self, data):
			self.output.append('<?' + data + '>')

	parser = CredentialHTML()
	parser.feed(html)
	parser.close()
	html = ''.join(parser.output)
	bootstrap = """<script>(function(){
const root = ROOT;
const local = value => { try { return new URL(value, location.href).href.startsWith(root); } catch { return false; } };
const originalFetch = window.fetch;
window.fetch = function(input, init) {
 if (local(input instanceof Request ? input.url : input)) init = Object.assign({}, init, {credentials: 'include'});
 return originalFetch.call(this, input, init);
};
const originalOpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url, ...rest) {
 const result = originalOpen.call(this, method, url, ...rest);
 if (local(url)) this.withCredentials = true;
 return result;
};
})();</script>""".replace('ROOT', json.dumps(asset_root))
	# After a leading doctype keeps standards mode while running before game code.
	match = re.match(r'\s*<!doctype[^>]*>', html, re.I)
	position = match.end() if match else 0
	return (html[:position] + bootstrap + html[position:]).encode('utf-8')


def prepare_css(raw, path, root, asset_root):
	"""Fonts use anonymous CORS, so embed package fonts in authenticated CSS."""
	def embed_font(match):
		url = match[1].strip().strip("\"'")
		parsed = urlsplit(url)
		if parsed.scheme or parsed.netloc:
			return match[0]
		resource = unquote(parsed.path)
		if resource.startswith('/game-assets/'):
			prefix = urlsplit(asset_root).path
			if not resource.startswith(prefix):
				return match[0]
			target = (root / resource[len(prefix):]).resolve()
		else:
			target = (path.parent / resource).resolve()
		if target.suffix.lower() not in ('.woff', '.woff2', '.ttf', '.otf') or not target.is_relative_to(root) or not target.is_file():
			return match[0]
		mime = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
		return 'url("data:' + mime + ';base64,' + base64.b64encode(target.read_bytes()).decode() + '")'
	return re.sub(r'url\(\s*([^)]*)\)', embed_font, raw.decode('utf-8-sig')).encode('utf-8')


class GamePackageRenderer(BaseRenderer):
	def can_render(self):
		return self.path.startswith('game-assets/')

	def render(self):
		from lms.lms.game import game_is_enabled
		from lms.lms.game_access import get_game_access
		# Resource responses, including denials, must not replace LMS login cookies.
		if getattr(frappe.local, 'cookie_manager', None):
			frappe.local.cookie_manager.cookies.clear()
			frappe.local.cookie_manager.to_delete.clear()
		# Frappe's page resolver removes .html; packaged assets need the exact
		# original request path for relative URLs and filenames to keep working.
		request_path = getattr(getattr(frappe.local, 'request', None), 'path', self.path)
		parts = request_path.lstrip('/').split('/', 2)
		if len(parts) != 3 or len(parts[1]) != 64 or any(c not in '0123456789abcdef' for c in parts[1]):
			raise frappe.PermissionError
		token, resource = parts[1:]
		access = frappe.cache.get_value('game-package:' + token)
		binding = getattr(getattr(frappe.local, 'request', None), 'cookies', {}).get('lms_game_session', '')
		if not access or not binding or not hmac.compare_digest(binding, access.get('binding', '')) or not session_is_active(access.get('sid'), access['user']) or not get_game_access(access['user'])['can_enter']:
			raise frappe.PermissionError
		if frappe.session.user != 'Guest' and frappe.session.sid != access.get('sid'):
			raise frappe.PermissionError
		if not frappe.db.exists('LMS Game', access['game']):
			raise frappe.DoesNotExistError
		if not game_is_enabled(access['game'], access['user']):
			raise frappe.PermissionError
		release = access.get('release')
		if release and frappe.db.get_value('LMS Game Release', release, 'game') != access['game']:
			raise frappe.PermissionError
		root = package_root(access['game'], release=release)
		path = (root / resource).resolve()
		if not path.is_relative_to(root) or not path.is_file():
			raise frappe.DoesNotExistError
		mime = {'.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm'}.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
		asset_root = frappe.local.request.host_url.rstrip('/') + '/game-assets/' + token + '/'
		body = path.read_bytes()
		if mime == 'text/html':
			body = prepare_html(body, asset_root)
		elif mime == 'text/css':
			body = prepare_css(body, path, root, asset_root)
		response = Response(body, mimetype=mime)
		from lms.lms.game_runtime import connection_sources
		connections = ' '.join(connection_sources(access['game'], release))
		policy = f"sandbox allow-scripts allow-pointer-lock; default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' {asset_root} https: blob:; style-src 'unsafe-inline' {asset_root} https:; img-src {asset_root} https: data: blob:; media-src {asset_root} https: data: blob:; font-src {asset_root} https: data:; connect-src {asset_root} {connections}; frame-src {asset_root}; worker-src blob:; base-uri 'none'; form-action 'none'"
		response.headers.update({
			'Content-Security-Policy': policy,
			'Access-Control-Allow-Origin': 'null',
			'Access-Control-Allow-Credentials': 'true',
			'Vary': 'Origin, Cookie',
			'Cross-Origin-Resource-Policy': 'cross-origin',
			'Referrer-Policy': 'no-referrer',
			'X-Content-Type-Options': 'nosniff',
			'Cache-Control': 'no-store',
		})
		return response
