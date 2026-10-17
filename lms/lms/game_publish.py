"""Front-end-only release publishing. Never builds images or operates Docker."""

import base64
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

import frappe

from lms.lms.game_package import store_package, validate_package

IDENTIFIER = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}')
MAX_PLAYERS = 8


def validate_manifest(manifest, game_key=None):
	if not isinstance(manifest, dict) or set(manifest) - {'manifestVersion', 'gameKey', 'release', 'platformApi', 'client', 'multiplayer'}:
		frappe.throw('Only front-end game manifest fields are allowed.')
	if manifest.get('manifestVersion') != 1 or manifest.get('platformApi') != '1':
		frappe.throw('Unsupported manifest or platform SDK version.')
	for key in ('gameKey', 'release'):
		if not isinstance(manifest.get(key), str) or not IDENTIFIER.fullmatch(manifest[key]):
			frappe.throw('Invalid game key or release version.')
	if game_key and manifest['gameKey'] != game_key:
		frappe.throw('Manifest gameKey does not match this game.')
	client = manifest.get('client')
	if not isinstance(client, dict) or set(client) - {'entry', 'type'} or client.get('type') not in ('html', 'zip'):
		frappe.throw('Manifest client must contain only entry and html/zip type.')
	if not isinstance(client.get('entry'), str) or len(client['entry']) > 512:
		frappe.throw('Invalid client entry.')
	mp = manifest.get('multiplayer')
	if not isinstance(mp, dict) or set(mp) - {'enabled', 'mode', 'compatibilityKey', 'minPlayers', 'maxPlayers', 'allowPrivateRoom', 'allowQuickMatch'}:
		frappe.throw('Invalid multiplayer configuration.')
	if mp.get('enabled') is not True or mp.get('mode') != 'relay':
		frappe.throw('This release requires multiplayer.enabled=true and mode=relay.')
	mp = dict(mp)
	mp.setdefault('compatibilityKey', manifest['release'])
	if not isinstance(mp['compatibilityKey'], str) or not IDENTIFIER.fullmatch(mp['compatibilityKey']):
		frappe.throw('Invalid compatibility key.')
	minimum, maximum = mp.get('minPlayers', 2), mp.get('maxPlayers', 4)
	if type(minimum) is not int or type(maximum) is not int or not 2 <= minimum <= maximum <= MAX_PLAYERS:
		frappe.throw('Relay rooms must allow between 2 and 8 players.')
	for key in ('allowPrivateRoom', 'allowQuickMatch'):
		mp.setdefault(key, True)
		if type(mp[key]) is not bool:
			frappe.throw('Room visibility settings must be booleans.')
	if not mp['allowPrivateRoom'] and not mp['allowQuickMatch']:
		frappe.throw('Enable private rooms or quick matching.')
	mp.update(minPlayers=minimum, maxPlayers=maximum)
	return {**manifest, 'multiplayer': mp}


def embedded_manifest(files, entry):
	path = str(PurePosixPath(entry).parent / 'game.manifest.json')
	if path not in files:
		return None
	try:
		if len(files[path]) > 16384:
			raise ValueError
		return json.loads(files[path].decode('utf-8'))
	except (ValueError, UnicodeDecodeError):
		frappe.throw('Invalid game.manifest.json (maximum 16 KiB).')


def _reject_server_files(files):
	for name in files:
		parts = [p.lower() for p in PurePosixPath(name).parts]
		base = parts[-1]
		if any(p in ('node_modules', 'server', '.git') for p in parts) or base in ('dockerfile', 'package.json', 'package-lock.json', 'yarn.lock') or base.startswith(('docker-compose', 'compose.')) or base.endswith(('.py', '.sh', '.exe', '.dll')):
			frappe.throw('Upload built browser assets only; server code and deployment files are not accepted.')


def publish_content(filename, content, title=None, manifest=None, multiplayer=None, game=None):
	from lms.lms.game import require_manager, validate_upload
	require_manager()
	filename = PurePosixPath(filename.replace('\\', '/')).name
	client_type = 'zip' if filename.lower().endswith('.zip') else 'html'
	files, entry = None, filename
	if client_type == 'zip':
		encoded, entry, files = validate_package(content)
		manifest = manifest or embedded_manifest(files, entry)
		_reject_server_files(files)
	else:
		encoded = validate_upload(filename, content)
	if game:
		# Serialize version checks and active pointer changes for this logical game.
		frappe.db.get_value('LMS Game', game, 'name', for_update=True)
		doc = frappe.get_doc('LMS Game', game)
		game_key = doc.game_key
	else:
		doc = None
		game_key = None
	if not manifest:
		options = dict(multiplayer or {})
		game_key = game_key or options.pop('gameKey', None) or 'game-' + secrets_key()
		release = options.pop('release', '1.0.0')
		manifest = {'manifestVersion': 1, 'gameKey': game_key, 'release': release, 'platformApi': '1', 'client': {'entry': entry, 'type': client_type}, 'multiplayer': {'enabled': True, 'mode': 'relay', **options}}
	# A ZIP may wrap its index and manifest in an outer directory, as static packages do.
	if files and isinstance(manifest, dict) and isinstance(manifest.get('client'), dict):
		declared = manifest['client'].get('entry')
		if isinstance(declared, str) and str(PurePosixPath(entry).parent / declared) == entry:
			manifest = {**manifest, 'client': {**manifest['client'], 'entry': entry}}
	manifest = validate_manifest(manifest, game_key)
	if manifest['client'] != {'entry': entry, 'type': client_type}:
		frappe.throw('Manifest entry/type does not match the uploaded file.')
	if not doc:
		if frappe.db.exists('LMS Game', {'game_key': manifest['gameKey']}):
			frappe.throw('Game key already exists. Select that game to publish a new version.')
		label = (title or PurePosixPath(filename).stem).strip()
		if not label or len(label) > 140 or len(filename) > 140:
			frappe.throw('Game title and filename must be between 1 and 140 characters.')
		doc = frappe.get_doc({'doctype': 'LMS Game', 'title': label, 'filename': filename, 'html_base64': encoded, 'entry_file': entry if files else '', 'enabled': 0, 'game_key': manifest['gameKey']}).insert(ignore_permissions=True)
	elif not doc.game_key:
		doc.game_key = manifest['gameKey']
		frappe.db.set_value('LMS Game', doc.name, 'game_key', doc.game_key)
	if frappe.db.exists('LMS Game Release', {'game': doc.name, 'version': manifest['release']}):
		frappe.throw('This release already exists; choose a new version.')
	release = frappe.get_doc({'doctype': 'LMS Game Release', 'game': doc.name, 'version': manifest['release'], 'game_key': manifest['gameKey'], 'manifest': json.dumps(manifest), 'client_sha256': hashlib.sha256(base64.b64decode(encoded)).hexdigest(), 'html_base64': encoded, 'entry_file': entry if files else '', 'filename': filename, 'client_type': client_type, 'platform_api': '1', 'compatibility_key': manifest['multiplayer']['compatibilityKey'], 'status': 'Ready'}).insert(ignore_permissions=True)
	if files:
		store_package(doc.name, files, release=release.name)
	activate_release(release.name)
	return {'name': doc.name, 'title': doc.title, 'filename': filename, 'release': release.name, 'runtime_mode': 'UniversalRelay'}


def secrets_key():
	import secrets
	return secrets.token_hex(8)


@frappe.whitelist(methods=['POST'])
def publish_release(filename: str, content: str, title: str | None = None, manifest: dict | None = None, multiplayer: dict | None = None, game: str | None = None):
	return publish_content(filename, content, title, manifest, multiplayer, game)


@frappe.whitelist(methods=['POST'])
def activate_release(release: str):
	from lms.lms.game import require_manager
	require_manager()
	doc = frappe.get_doc('LMS Game Release', release)
	if doc.status != 'Ready':
		frappe.throw('Release is not ready.')
	frappe.db.get_value('LMS Game', doc.game, 'name', for_update=True)
	validate_manifest(json.loads(doc.manifest), frappe.db.get_value('LMS Game', doc.game, 'game_key'))
	frappe.db.set_value('LMS Game', doc.game, {'runtime_mode': 'UniversalRelay', 'active_release': release, 'filename': doc.filename, 'entry_file': doc.entry_file})
	frappe.publish_realtime('lms_game_visibility_changed', room='website', after_commit=True)
	return {'game': doc.game, 'release': release}


def publish_from_files(manifest_path, client_path, game=None, title=None):
	"""Trusted local convenience; publishing still only updates front-end data."""
	filename = Path(client_path).name
	result = publish_content(filename, base64.b64encode(Path(client_path).read_bytes()).decode(), title, json.loads(Path(manifest_path).read_text()), game=game)
	frappe.db.commit()
	return result
