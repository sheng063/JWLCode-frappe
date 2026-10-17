"""Fixed universal relay authorization. Game frames never receive an LMS session."""

import base64
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
ACTIONS = ('createRoom', 'quickMatch', 'joinRoom')


def _key(kind, token):
	if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{64}', token):
		_deny()
	return frappe.cache.make_key(PREFIX + kind + ':' + token)


def _put(kind, token, value, ttl):
	frappe.cache.set(_key(kind, token), json.dumps(value), ex=ttl)


def _get(kind, token):
	raw = frappe.cache.get(_key(kind, token))
	return json.loads(raw) if raw else None


def _deny():
	frappe.flags.disable_traceback = True
	frappe.throw('联机授权无效或已过期，请重新进入游戏。', frappe.PermissionError)


def _rate_limit(identity, limit=30):
	key = frappe.cache.make_key(PREFIX + 'rate:' + identity + ':' + str(int(time.time() // 60)))
	count = frappe.cache.incr(key)
	if count == 1:
		frappe.cache.expire(key, 65)
	if count > limit:
		frappe.throw('联机请求过于频繁，请稍后重试。', frappe.RateLimitExceededError)


def _runtime_config():
	from frappe.config import get_site_config
	return get_site_config(cached=False)


def runtime_config(*, existing=False):
	config = _runtime_config().get('game_universal_runtime') or {}
	statuses = ('Ready', 'Draining') if existing else ('Ready',)
	if config.get('status') not in statuses or config.get('protocolVersion') != 1:
		frappe.throw('通用联机服务尚未就绪，请稍后重试。')
	validate_endpoint(config.get('endpoint'))
	return config


def validate_endpoint(endpoint):
	if not isinstance(endpoint, str):
		frappe.throw('Invalid universal runtime endpoint.')
	url = urlsplit(endpoint)
	if not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/') or re.search(r'[\s;\'"<>]', endpoint):
		frappe.throw('Runtime endpoint must be a fixed origin.')
	if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1')):
		frappe.throw('Runtime endpoint requires HTTPS except on localhost.')
	return endpoint.rstrip('/')


def connection_sources(game, release=None):
	if not release:
		return []
	row = frappe.db.get_value('LMS Game Release', release, ['game', 'platform_api'], as_dict=True)
	if not row or row.game != game:
		_deny()
	if row.platform_api != '1':
		return []
	endpoint = runtime_config(existing=True)['endpoint']
	return [endpoint, re.sub(r'^http', 'ws', endpoint)]


def _launch_allowed(launch, evaluator=None):
	if not launch or launch.get('protocol') != 1 or launch['expires_at'] <= time.time():
		return False
	if not session_is_active(launch['sid'], launch['user']):
		return False
	from lms.lms.game import can_manage_games
	evaluator = evaluator or AccessEvaluator([launch['user']])
	if not evaluator.evaluate(launch['user'], manager=can_manage_games(launch['user']))['can_enter'] or not game_is_enabled(launch['game'], launch['user']):
		return False
	game = frappe.db.get_value('LMS Game', launch['game'], ['runtime_mode', 'game_key'], as_dict=True)
	release = frappe.db.get_value('LMS Game Release', launch['release'], ['status', 'game', 'game_key', 'platform_api'], as_dict=True)
	config = _runtime_config().get('game_universal_runtime') or {}
	return bool(game and game.runtime_mode == 'UniversalRelay' and game.game_key == launch['game_key'] and release and release.status == 'Ready' and release.game == launch['game'] and release.game_key == game.game_key and release.platform_api == '1' and config.get('status') in ('Ready', 'Draining') and config.get('protocolVersion') == 1)


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
	if doc.runtime_mode != 'UniversalRelay' or not doc.active_release:
		frappe.throw('This game has no universal relay release.')
	from lms.lms.game_publish import validate_manifest
	release = frappe.get_doc('LMS Game Release', doc.active_release)
	if release.game != game or release.status != 'Ready':
		_deny()
	manifest = validate_manifest(json.loads(release.manifest), doc.game_key)
	config = runtime_config()
	if not frappe.session.sid or frappe.session.sid == 'Guest':
		_deny()
	launch_id = secrets.token_hex(32)
	launch = {'protocol': 1, 'site': frappe.local.site, 'user': frappe.session.user, 'sid': frappe.session.sid, 'game': game, 'game_key': doc.game_key, 'release': release.name, 'compatibility_key': manifest['multiplayer']['compatibilityKey'], 'scope': frappe.local.site, 'expires_at': time.time() + LAUNCH_TTL}
	_put('launch', launch_id, launch, LAUNCH_TTL)
	result = {'launch_id': launch_id, 'endpoint': config['endpoint'], 'release': release.version, 'title': doc.title, 'platform_api': 1, 'multiplayer': manifest['multiplayer'], 'connect_sources': connection_sources(game, release.name)}
	if release.entry_file:
		from lms.lms.game_package import launch_url
		result['url'] = launch_url(doc, release=release)
	else:
		result['html'] = base64.b64decode(release.html_base64).decode('utf-8')
	return result


@frappe.whitelist(methods=['POST'])
def issue_join_ticket(launch_id: str, action: str, room_id: str = '', max_players: int | None = None, visibility: str = 'private'):
	launch = _owned_launch(launch_id)
	_rate_limit('ticket:' + frappe.session.user)
	if action not in ACTIONS or not _launch_allowed(launch):
		_deny()
	config = runtime_config()
	mp = json.loads(frappe.db.get_value('LMS Game Release', launch['release'], 'manifest'))['multiplayer']
	if action == 'joinRoom':
		room_id = room_id.strip().upper()
		if not re.fullmatch(r'[A-Z0-9]{6,12}', room_id):
			frappe.throw('请输入有效的房间号。')
	elif room_id:
		_deny()
	if action == 'quickMatch':
		if not mp['allowQuickMatch']:
			_deny()
		visibility = 'public'
	elif action == 'createRoom':
		if visibility not in ('private', 'public') or not mp['allowPrivateRoom' if visibility == 'private' else 'allowQuickMatch']:
			_deny()
	maximum = min(mp['maxPlayers'], 8)
	players = maximum if max_players is None else max_players
	if type(players) is not int or not mp['minPlayers'] <= players <= maximum:
		frappe.throw('房间人数超出该游戏允许的范围。')
	ticket = secrets.token_hex(32)
	_put('ticket', ticket, {'launch_id': launch_id, 'action': action, 'room_id': room_id, 'max_players': players, 'visibility': visibility}, TICKET_TTL)
	return {'ticket': ticket, 'endpoint': config['endpoint'], 'room_type': 'universal', 'room_id': room_id, 'action': action}


@frappe.whitelist(methods=['POST'])
def close_launch(launch_id: str):
	_owned_launch(launch_id)
	frappe.cache.delete(_key('launch', launch_id))
	return {'closed': True}


def _service():
	provided = frappe.get_request_header('X-Game-Service-Key') or ''
	config = _runtime_config().get('game_universal_runtime') or {}
	expected = config.get('service_key', '')
	if frappe.get_request_header('X-Game-Runtime') != 'universal' or not expected or not provided.isascii() or len(provided) > 256 or not hmac.compare_digest(provided, expected):
		_deny()
	return config


@frappe.whitelist(allow_guest=True, methods=['POST'])
def redeem_ticket(ticket: str, action: str, room_id: str = ''):
	config = _service()
	if config.get('status') != 'Ready' or action not in ACTIONS:
		_deny()
	script = """local raw = redis.call('GET', KEYS[1]); if not raw then return false end;
	local v = cjson.decode(raw); if v.action ~= ARGV[1] or v.room_id ~= ARGV[2] then return false end;
	redis.call('DEL', KEYS[1]); return raw"""
	raw = frappe.cache.eval(script, 1, _key('ticket', ticket), action, room_id)
	if not raw:
		_deny()
	claim = json.loads(raw)
	launch = _get('launch', claim['launch_id'])
	if not _launch_allowed(launch):
		_deny()
	lease = secrets.token_hex(32)
	_put('lease', lease, {'launch_id': claim['launch_id'], 'protocol': 1}, LAUNCH_TTL)
	from frappe.utils.password import get_encryption_key
	player = hmac.new(get_encryption_key().encode(), (launch['site'] + ':' + launch['user']).encode(), hashlib.sha256).hexdigest()[:24]
	mp = json.loads(frappe.db.get_value('LMS Game Release', launch['release'], 'manifest'))['multiplayer']
	return {'lease_id': lease, 'lease_seconds': LEASE_TTL, 'player_id': player, 'site': launch['site'], 'scope': launch['scope'], 'release': launch['release'], 'game': launch['game'], 'game_key': launch['game_key'], 'compatibility_key': launch['compatibility_key'], 'action': action, 'room_id': room_id, 'max_players': claim['max_players'], 'visibility': claim['visibility'], 'permissions': mp}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def renew_leases(lease_ids: list[str]):
	_service()
	if not isinstance(lease_ids, list) or len(lease_ids) > 100:
		frappe.throw('Invalid lease batch.')
	claims = {lease: _get('lease', lease) for lease in lease_ids}
	launches = {lease: _get('launch', claim['launch_id']) for lease, claim in claims.items() if claim and claim.get('protocol') == 1}
	evaluator = AccessEvaluator([launch['user'] for launch in launches.values() if launch])
	return {'valid': [lease for lease, launch in launches.items() if _launch_allowed(launch, evaluator)], 'lease_seconds': LEASE_TTL}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def service_status():
	config = _service()
	return {'status': config.get('status', 'Stopped'), 'protocolVersion': config.get('protocolVersion')}


def configure_runtime(endpoint, service_key_path, status='Ready'):
	"""One-time, trusted admin CLI setup. Not a game publishing operation."""
	frappe.only_for('System Manager')
	from pathlib import Path
	from frappe.installer import update_site_config
	endpoint = validate_endpoint(endpoint)
	secret = Path(service_key_path).read_text().strip()
	if len(secret) < 32 or status not in ('Ready', 'Draining', 'Stopped'):
		frappe.throw('Invalid universal runtime configuration.')
	update_site_config('game_universal_runtime', {'endpoint': endpoint, 'service_key': secret, 'status': status, 'protocolVersion': 1})
	return {'endpoint': endpoint, 'status': status, 'room_type': 'universal'}
