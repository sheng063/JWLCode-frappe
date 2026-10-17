"""Trusted CLI release registration. Deliberately not HTTP-whitelisted."""

import base64
import hashlib
import json
import re
from pathlib import Path

import frappe

from lms.lms.game_package import store_package, validate_package, package_root
from lms.lms.game_runtime import validate_endpoint


def validate_manifest(manifest):
	if not isinstance(manifest, dict) or manifest.get('manifestVersion') != 1 or manifest.get('platformApi') != '1' or manifest.get('runtimeProfile') != 'colyseus-web-v1':
		frappe.throw('Unsupported game manifest or runtime profile.')
	for key in ('gameKey', 'release'):
		if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}', manifest.get(key, '')):
			frappe.throw('Invalid manifest identifier.')
	client = manifest.get('client', {})
	if not re.fullmatch(r'[a-f0-9]{64}', client.get('sha256', '')):
		frappe.throw('Client SHA256 is required.')
	server = manifest.get('server', {})
	if server.get('protocolVersion') != '1' or not re.fullmatch(r'.+@sha256:[a-f0-9]{64}', server.get('image', '')):
		frappe.throw('An immutable server image digest and protocolVersion 1 are required.')
	rooms = manifest.get('rooms', [])
	if not isinstance(rooms, list) or not 1 <= len(rooms) <= 20:
		frappe.throw('Manifest must declare 1–20 room types.')
	seen = set()
	for room in rooms:
		key = room.get('key', '')
		if not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', key) or key in seen or type(room.get('maxClients')) is not int or not 2 <= room['maxClients'] <= 100 or room.get('visibility') not in ('private', 'public'):
			frappe.throw('Invalid room definition.')
		seen.add(key)
	limits = manifest.get('limits', {})
	for key, ceiling in [('maxRooms', 1000), ('maxConnections', 10000), ('memoryMiB', 16384)]:
		if type(limits.get(key)) is not int or not 1 <= limits[key] <= ceiling:
			frappe.throw('Invalid runtime limits.')
	return manifest


def publish_release(manifest_path, client_path, endpoint, service_key=None, game=None, title=None, service_key_path=None):
	"""bench execute ... --kwargs ...; deploy and verify runtime before activate_release."""
	frappe.only_for('System Manager')
	if service_key_path:
		service_key = Path(service_key_path).read_text().strip()
	manifest = validate_manifest(json.loads(Path(manifest_path).read_text()))
	endpoint = validate_endpoint(endpoint)
	if not isinstance(service_key, str) or len(service_key) < 32:
		frappe.throw('Service key must contain at least 32 characters.')
	content = Path(client_path).read_bytes()
	if hashlib.sha256(content).hexdigest() != manifest['client']['sha256']:
		frappe.throw('Client artifact checksum mismatch.')
	encoded, entry, files = validate_package(base64.b64encode(content).decode())
	if entry != manifest['client']['entry']:
		frappe.throw('Client entry does not match manifest.')
	if game:
		game_doc = frappe.get_doc('LMS Game', game)
	else:
		game_doc = frappe.get_doc({'doctype': 'LMS Game', 'title': title or manifest['gameKey'], 'filename': manifest['gameKey'] + '.zip', 'html_base64': encoded, 'entry_file': entry, 'enabled': 0}).insert(ignore_permissions=True)
		store_package(game_doc.name, files)
	if frappe.db.exists('LMS Game Release', {'game': game_doc.name, 'version': manifest['release']}):
		frappe.throw('This game version already exists. Publish a new version.')
	release = frappe.get_doc({'doctype': 'LMS Game Release', 'game': game_doc.name, 'version': manifest['release'], 'game_key': manifest['gameKey'], 'manifest': json.dumps(manifest), 'client_sha256': manifest['client']['sha256'], 'html_base64': encoded, 'entry_file': entry, 'runtime_profile': manifest['runtimeProfile'], 'server_image': manifest['server']['image'], 'status': 'Ready'}).insert(ignore_permissions=True)
	store_package(game_doc.name, files, release=release.name)
	deployment = frappe.get_doc({'doctype': 'LMS Game Deployment', 'release': release.name, 'endpoint': endpoint, 'status': 'Starting'}).insert(ignore_permissions=True)
	keys = dict(frappe.conf.get('game_runtime_service_keys') or {})
	keys[deployment.name] = service_key
	from frappe.installer import update_site_config
	update_site_config('game_runtime_service_keys', keys)
	frappe.conf.game_runtime_service_keys = keys
	frappe.db.commit()
	return {'game': game_doc.name, 'release': release.name, 'deployment': deployment.name}


def activate_release(deployment):
	frappe.only_for('System Manager')
	dep = frappe.get_doc('LMS Game Deployment', deployment)
	release = frappe.get_doc('LMS Game Release', dep.release)
	if release.status != 'Ready' or dep.status == 'Stopped':
		frappe.throw('Release cannot be activated.')
	validate_endpoint(dep.endpoint)
	# The deployment Worker must verify /readyz AND a real room join before calling.
	old = frappe.db.get_value('LMS Game', release.game, 'active_release')
	if old and old != release.name:
		for row in frappe.get_all('LMS Game Deployment', filters={'release': old, 'status': 'Ready'}, pluck='name'):
			frappe.db.set_value('LMS Game Deployment', row, 'status', 'Draining')
	dep.status = 'Ready'
	dep.save(ignore_permissions=True)
	frappe.db.set_value('LMS Game', release.game, {'runtime_mode': 'Colyseus', 'active_release': release.name})
	frappe.publish_realtime('lms_game_visibility_changed', room='website', after_commit=True)
	frappe.db.commit()
	return {'game': release.game, 'release': release.name, 'deployment': dep.name}


def approve_local_origin(endpoint):
	"""Local CLI convenience; remote origins require explicit site configuration."""
	from urllib.parse import urlsplit
	from frappe.installer import update_site_config
	frappe.only_for('System Manager')
	parsed = urlsplit(endpoint)
	if parsed.scheme != 'http' or parsed.hostname != 'localhost' or not parsed.port or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
		frappe.throw('Only a localhost HTTP origin can be auto-approved.')
	origins = list(frappe.conf.get('game_runtime_allowed_origins') or [])
	if endpoint not in origins:
		origins.append(endpoint)
		update_site_config('game_runtime_allowed_origins', origins)
	return {'approved': endpoint}


def stop_deployment(deployment):
	frappe.only_for('System Manager')
	frappe.db.set_value('LMS Game Deployment', deployment, 'status', 'Stopped')
	frappe.db.commit()
	return {'stopped': deployment}


def prepare_deployment(deployment):
	"""CLI: mark a retained deployment as Starting before bringing its stack up."""
	frappe.only_for('System Manager')
	dep = frappe.get_doc('LMS Game Deployment', deployment)
	if dep.status == 'Ready':
		frappe.throw('Deployment is already active.')
	frappe.db.set_value('LMS Game Deployment', deployment, 'status', 'Starting')
	frappe.db.commit()
	return {'starting': deployment}
