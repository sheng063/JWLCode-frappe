"""Game control plane. Browser credentials never reach a Colyseus worker."""

import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import urlsplit

import frappe

from lms.lms.game import game_is_enabled, require_access
from lms.lms.game_access import AccessEvaluator
from lms.lms.game_package import session_is_active

LAUNCH_TTL = 8 * 60 * 60
TICKET_TTL = 60
LEASE_TTL = 30
PREFIX = 'game-runtime:'


def _key(kind, token):
	if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{64}', token):
		frappe.throw('Invalid game credential.', frappe.PermissionError)
	return frappe.cache.make_key(PREFIX + kind + ':' + token)


def _put(kind, token, value, ttl):
	# Raw JSON avoids request-local cache and fails closed on Redis errors.
	frappe.cache.set(_key(kind, token), json.dumps(value), ex=ttl)


def _get(kind, token):
	raw = frappe.cache.get(_key(kind, token))
	return json.loads(raw) if raw else None


def _deny():
	frappe.flags.disable_traceback = True
	frappe.throw('Game authorization is no longer valid.', frappe.PermissionError)


def _rate_limit(identity, limit=30):
	bucket = int(time.time() // 60)
	key = frappe.cache.make_key(PREFIX + 'rate:' + identity + ':' + str(bucket))
	count = frappe.cache.incr(key)
	if count == 1:
		frappe.cache.expire(key, 65)
	if count > limit:
		frappe.throw('Too many game requests. Try again shortly.', frappe.RateLimitExceededError)


def _runtime_config():
	# Web workers cache site config independently; deployments must not require a restart.
	from frappe.config import get_site_config
	return get_site_config(cached=False)


def validate_endpoint(endpoint):
	if not isinstance(endpoint, str):
		frappe.throw('Invalid runtime endpoint.')
	parsed = urlsplit(endpoint)
	if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
		frappe.throw('Runtime endpoint must be an origin.')
	if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
		frappe.throw('Runtime endpoint requires HTTPS (except localhost).')
	origin = endpoint.rstrip('/')
	if origin not in (_runtime_config().get('game_runtime_allowed_origins') or []):
		frappe.throw('Runtime origin is not approved in site configuration.')
	return origin


def deployment_for(release, *, existing=False):
	statuses = ['Ready', 'Draining'] if existing else ['Ready']
	rows = frappe.get_all('LMS Game Deployment', filters={'release': release, 'status': ['in', statuses]}, fields=['name', 'release', 'endpoint', 'status'], order_by='creation desc', limit=1)
	if not rows:
		frappe.throw('联机服务尚未就绪，请稍后重试。')
	row = rows[0]
	validate_endpoint(row.endpoint)
	return row


def connection_sources(game, release=None):
	if not release:
		return []
	if frappe.db.get_value('LMS Game Release', release, 'game') != game:
		_deny()
	dep = deployment_for(release, existing=True)
	endpoint = validate_endpoint(dep.endpoint)
	return [endpoint, re.sub(r'^http', 'ws', endpoint)]


def _launch_allowed(launch, evaluator=None):
	if not launch or launch['expires_at'] <= time.time():
		return False
	if not session_is_active(launch['sid'], launch['user']):
		return False
	evaluator = evaluator or AccessEvaluator([launch['user']])
	from lms.lms.game import can_manage_games
	if not evaluator.evaluate(launch['user'], manager=can_manage_games(launch['user']))['can_enter']:
		return False
	if not game_is_enabled(launch['game'], launch['user']):
		return False
	if not frappe.db.exists('LMS Game', launch['game']):
		return False
	dep = frappe.db.get_value('LMS Game Deployment', launch['deployment'], ['release', 'status'], as_dict=True)
	return bool(dep and dep.release == launch['release'] and dep.status in ('Ready', 'Draining') and frappe.db.get_value('LMS Game Release', launch['release'], 'status') == 'Ready')


def _owned_launch(launch_id):
	launch = _get('launch', launch_id)
	if not launch or launch['user'] != frappe.session.user or launch['sid'] != frappe.session.sid:
		_deny()
	return launch


@frappe.whitelist(methods=['POST'])
def create_launch(game: str):
	require_access(game)
	_rate_limit('launch:' + frappe.session.user)
	doc = frappe.get_doc('LMS Game', game)
	if doc.runtime_mode != 'Colyseus' or not doc.active_release:
		frappe.throw('This game has no active multiplayer release.')
	release = frappe.get_doc('LMS Game Release', doc.active_release)
	if release.game != game or release.status != 'Ready':
		_deny()
	dep = deployment_for(release.name)
	if not frappe.session.sid or frappe.session.sid == 'Guest':
		_deny()
	nonce = secrets.token_hex(32)
	launch = {'site': frappe.local.site, 'user': frappe.session.user, 'sid': frappe.session.sid, 'game': game, 'release': release.name, 'deployment': dep.name, 'scope': frappe.local.site, 'expires_at': time.time() + LAUNCH_TTL}
	_put('launch', nonce, launch, LAUNCH_TTL)
	result = {'launch_id': nonce, 'endpoint': dep.endpoint, 'release': release.version, 'title': doc.title, 'room_keys': [r['key'] for r in json.loads(release.manifest)['rooms']], 'connect_sources': connection_sources(game, release.name)}
	if release.entry_file:
		from lms.lms.game_package import launch_url
		result['url'] = launch_url(doc, release=release)
	else:
		import base64
		result['html'] = base64.b64decode(release.html_base64).decode('utf-8')
	return result


@frappe.whitelist(methods=['POST'])
def issue_join_ticket(launch_id: str, room_key: str):
	launch = _owned_launch(launch_id)
	_rate_limit('ticket:' + frappe.session.user)
	if not _launch_allowed(launch) or frappe.db.get_value('LMS Game Deployment', launch['deployment'], 'status') != 'Ready':
		_deny()
	manifest = json.loads(frappe.db.get_value('LMS Game Release', launch['release'], 'manifest'))
	if room_key not in [room['key'] for room in manifest['rooms']]:
		_deny()
	ticket = secrets.token_hex(32)
	_put('ticket', ticket, {'launch_id': launch_id, 'room_key': room_key, 'deployment': launch['deployment']}, TICKET_TTL)
	return {'ticket': ticket, 'endpoint': frappe.db.get_value('LMS Game Deployment', launch['deployment'], 'endpoint'), 'room_type': room_key}


@frappe.whitelist(methods=['POST'])
def close_launch(launch_id: str):
	_owned_launch(launch_id)
	frappe.cache.delete(_key('launch', launch_id))
	return {'closed': True}


def _service():
	deployment = frappe.get_request_header('X-Game-Deployment') or ''
	provided = frappe.get_request_header('X-Game-Service-Key') or ''
	expected = (_runtime_config().get('game_runtime_service_keys') or {}).get(deployment, '')
	if not expected or len(provided) > 256 or not hmac.compare_digest(provided, expected):
		_deny()
	if not frappe.db.exists('LMS Game Deployment', deployment):
		_deny()
	return deployment


@frappe.whitelist(allow_guest=True, methods=['POST'])
def redeem_ticket(ticket: str, room_key: str):
	deployment = _service()
	# Binding check and deletion happen in one Redis operation, including across workers.
	script = """local raw = redis.call('GET', KEYS[1]); if not raw then return false end;
	local v = cjson.decode(raw); if v.deployment ~= ARGV[1] or v.room_key ~= ARGV[2] then return false end;
	redis.call('DEL', KEYS[1]); return raw"""
	raw = frappe.cache.eval(script, 1, _key('ticket', ticket), deployment, room_key)
	if not raw:
		_deny()
	claim = json.loads(raw)
	launch = _get('launch', claim['launch_id'])
	if not _launch_allowed(launch) or launch['deployment'] != deployment or frappe.db.get_value('LMS Game Deployment', deployment, 'status') != 'Ready':
		_deny()
	lease = secrets.token_hex(32)
	_put('lease', lease, {'launch_id': claim['launch_id'], 'deployment': deployment}, LAUNCH_TTL)
	# Stable pseudonymous player ID, no email or Frappe session secret.
	from frappe.utils.password import get_encryption_key
	player = hmac.new(get_encryption_key().encode(), (launch['site'] + ':' + launch['user']).encode(), hashlib.sha256).hexdigest()[:24]
	return {'lease_id': lease, 'lease_seconds': LEASE_TTL, 'player_id': player, 'scope': launch['scope'], 'release': launch['release'], 'game': launch['game'], 'deployment': deployment}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def renew_leases(lease_ids: list[str]):
	deployment = _service()
	if not isinstance(lease_ids, list) or len(lease_ids) > 100:
		frappe.throw('Invalid lease batch.')
	claims = {lease: _get('lease', lease) for lease in lease_ids}
	launches = {lease: _get('launch', claim['launch_id']) for lease, claim in claims.items() if claim and claim['deployment'] == deployment}
	evaluator = AccessEvaluator([launch['user'] for launch in launches.values() if launch])
	return {'valid': [lease for lease, launch in launches.items() if _launch_allowed(launch, evaluator)], 'lease_seconds': LEASE_TTL}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def service_status():
	deployment = _service()
	return frappe.db.get_value('LMS Game Deployment', deployment, ['name', 'release', 'status'], as_dict=True)
