import { randomBytes } from 'node:crypto';
import { Room, ServerError } from '@colyseus/core';
import { Schema, MapSchema, defineTypes } from '@colyseus/schema';

class Player extends Schema {
  constructor(id, label) { super(); this.id = id; this.label = label; this.connected = true; }
}
defineTypes(Player, { id: 'string', label: 'string', connected: 'boolean' });
class Roster extends Schema {
  constructor() { super(); this.players = new MapSchema(); this.hostId = ''; this.roomCode = ''; }
}
defineTypes(Roster, { players: { map: Player }, hostId: 'string', roomCode: 'string' });

export const defaultLimits = Object.freeze({ maxPlayers: 8, maxRooms: 100, maxConnections: 256, maxConnectionsPerUser: 4, maxRoomsPerUser: 2, maxMessageBytes: 16384, maxMessagesPerSecond: 60, roomLifetimeSeconds: 3600, reconnectSeconds: 20 });
export function createPool() {
  return { accepting: false, rooms: new Map(), connections: new Map(), seats: new Map(), owned: new Map(), forwarded: 0, bytesIn: 0, bytesOut: 0 };
}
const deny = message => new ServerError(403, message || 'Room authorization denied');
const userKey = auth => JSON.stringify([auth.site, auth.player_id]);
const isolation = auth => JSON.stringify([auth.site, auth.game, auth.game_key, auth.compatibility_key, auth.scope]);
export function assertRoomAccess(room, auth) {
  if (room.isolation !== isolation(auth) || room.maxClients < auth.permissions.minPlayers || room.maxClients > auth.permissions.maxPlayers ||
      !auth.permissions[room.visibility === 'private' ? 'allowPrivateRoom' : 'allowQuickMatch']) throw deny('This room belongs to another game or compatibility group');
}
function safeJson(value, depth = 0) {
  if (depth > 16) return false;
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return true;
  if (typeof value === 'number') return Number.isFinite(value);
  if (Array.isArray(value)) return value.length <= 4096 && value.every(x => safeJson(x, depth + 1));
  return typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype && Object.keys(value).length <= 1024 && Object.values(value).every(x => safeJson(x, depth + 1));
}
export function validateEnvelope(message, previousSeq, maxBytes) {
  if (!message || typeof message !== 'object' || message.protocol !== 1 ||
      typeof message.type !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9:_.\/-]{0,63}$/.test(message.type) || message.type.startsWith('platform:') ||
      !Number.isSafeInteger(message.seq) || message.seq <= previousSeq || !safeJson(message.payload) ||
      (message.to !== undefined && (typeof message.to !== 'string' || message.to.length > 64)) ||
      (message.echo !== undefined && typeof message.echo !== 'boolean')) throw deny('Invalid relay envelope');
  const bytes = Buffer.byteLength(JSON.stringify(message), 'utf8');
  if (bytes > maxBytes) throw new ServerError(413, 'Relay message is too large');
  return bytes;
}

export function universalRoom({ control, pool, limits = defaultLimits }) {
  return class UniversalRoom extends Room {
    static async onAuth(token, options, context) {
      if (!pool.accepting || !/^[a-f0-9]{64}$/.test(token || '') || !context?.platformAction) throw deny();
      const auth = await control.call('redeem_ticket', { ticket: token, action: context.platformAction, room_id: context.platformRoomId || '' });
      if (auth.action !== context.platformAction || auth.room_id !== (context.platformRoomId || '') || !auth.site || !auth.game || !auth.game_key || !auth.scope || !auth.compatibility_key) throw deny();
      if (!Number.isInteger(auth.max_players) || auth.max_players < 2 || auth.max_players > limits.maxPlayers) throw deny();
      if (auth.action === 'joinRoom') {
        const room = pool.rooms.get(auth.room_id);
        if (!room) throw new ServerError(404, 'Room does not exist');
        assertRoomAccess(room, auth);
      }
      for (const [id, seat] of pool.seats) if (seat.until <= performance.now()) pool.seats.delete(id);
      const owner = userKey(auth);
      const reservations = [...pool.seats.values()].filter(x => x.owner === owner).length;
      if ([...pool.connections.values()].reduce((a, b) => a + b, 0) + pool.seats.size >= limits.maxConnections ||
          (pool.connections.get(owner) || 0) + reservations >= limits.maxConnectionsPerUser) throw new ServerError(429, 'Connection quota reached');
      pool.seats.set(auth.lease_id, { owner, until: performance.now() + 15000 });
      options.partition = JSON.stringify([isolation(auth), auth.visibility, auth.max_players]);
      options.platform = { isolation: isolation(auth), owner, visibility: auth.visibility, maxPlayers: auth.max_players, site: auth.site, gameKey: auth.game_key, release: auth.release };
      return auth;
    }
    async onCreate(options) {
      const spec = options.platform;
      if (!pool.accepting || !spec || pool.rooms.size >= limits.maxRooms || (pool.owned.get(spec.owner) || 0) >= limits.maxRoomsPerUser) throw new ServerError(429, 'Room quota reached');
      this.isolation = spec.isolation;
      this.visibility = spec.visibility;
      this.owner = spec.owner;
      this.maxClients = spec.maxPlayers;
      this.maxMessagesPerSecond = limits.maxMessagesPerSecond;
      this.seatReservationTimeout = 10;
      this.autoDispose = true;
      do { this.roomId = randomBytes(4).toString('hex').toUpperCase(); } while (pool.rooms.has(this.roomId));
      this.setState(new Roster());
      this.state.roomCode = this.roomId;
      this.patchRate = 100;
      this.leases = new Map();
      this.refreshing = false;
      pool.rooms.set(this.roomId, this);
      pool.owned.set(this.owner, (pool.owned.get(this.owner) || 0) + 1);
      this.clock.setInterval(() => this.expireLeases(), 250);
      this.clock.setInterval(() => this.refreshLeases(), 5000);
      this.clock.setTimeout(() => {
        this.broadcast('platform:roomClosed', { reason: 'Room lifetime exceeded' });
        this.disconnect(4004);
      }, limits.roomLifetimeSeconds * 1000);
      this.onMessage('relay', (client, message) => this.relay(client, message));
      await this.setPrivate(this.visibility === 'private');
      console.log(JSON.stringify({ event: 'room_created', site: spec.site, gameKey: spec.gameKey, release: spec.release, roomId: this.roomId, roomType: 'universal' }));
    }
    async onJoin(client, options, auth) {
      assertRoomAccess(this, auth);
      if (auth.action === 'joinRoom' && auth.room_id !== this.roomId) throw deny();
      const result = await control.call('renew_leases', { lease_ids: [auth.lease_id] });
      if (!result.valid.includes(auth.lease_id)) throw deny();
      const owner = userKey(auth);
      pool.seats.delete(auth.lease_id);
      if ((pool.connections.get(owner) || 0) >= limits.maxConnectionsPerUser) throw deny('Connection quota reached');
      pool.connections.set(owner, (pool.connections.get(owner) || 0) + 1);
      this.leases.set(client.sessionId, { client, auth, until: performance.now() + result.lease_seconds * 1000, seq: -1, owner });
      this.state.players.set(client.sessionId, new Player(client.sessionId, auth.player_id.slice(0, 8)));
      this.electHost();
    }
    electHost() {
      if (this.state.players.get(this.state.hostId)?.connected) return;
      this.state.hostId = [...this.state.players.values()].find(player => player.connected)?.id || '';
    }
    relay(client, message) {
      const lease = this.leases.get(client.sessionId);
      if (!lease || lease.until <= performance.now()) { client.leave(4003, 'Game authorization expired'); return; }
      try {
        pool.bytesIn += validateEnvelope(message, lease.seq, limits.maxMessageBytes);
        lease.seq = message.seq;
        const envelope = { from: client.sessionId, type: message.type, payload: message.payload, seq: message.seq };
        const targets = this.clients.filter(target => message.to ? target.sessionId === message.to : target.sessionId !== client.sessionId || message.echo === true);
        for (const target of targets) {
          target.send('relay', envelope);
          pool.forwarded++;
          pool.bytesOut += Buffer.byteLength(JSON.stringify(envelope));
        }
      } catch { lease.until = 0; client.leave(4008, 'Invalid or excessive relay message'); }
    }
    expireLeases() {
      for (const lease of this.leases.values()) if (lease.until <= performance.now()) lease.client.leave(4003, 'Game authorization expired');
    }
    async refreshLeases() {
      if (this.refreshing || !this.leases.size) return;
      this.refreshing = true;
      try {
        const snapshot = [...this.leases.values()];
        for (let offset = 0; offset < snapshot.length; offset += 100) {
          const batch = snapshot.slice(offset, offset + 100);
          const result = await control.call('renew_leases', { lease_ids: batch.map(x => x.auth.lease_id) });
          for (const lease of batch) {
            if (result.valid.includes(lease.auth.lease_id)) lease.until = performance.now() + result.lease_seconds * 1000;
            else { lease.until = 0; lease.client.leave(4003, 'Game access revoked'); }
          }
        }
      } catch { /* Authorization expires on schedule even if Frappe is unavailable. */ }
      finally { this.refreshing = false; }
    }
    async onDrop(client, code) {
      if (code >= 4000 && code !== 4010) return; // 4010 is the native SDK network-retry signal.
      const lease = this.leases.get(client.sessionId);
      if (!lease || lease.until <= performance.now()) return;
      this.state.players.get(client.sessionId).connected = false;
      this.electHost();
      try { await this.allowReconnection(client, limits.reconnectSeconds); } catch { /* onLeave follows. */ }
    }
    async onReconnect(client) {
      const lease = this.leases.get(client.sessionId);
      if (!lease) throw deny();
      const result = await control.call('renew_leases', { lease_ids: [lease.auth.lease_id] });
      if (!result.valid.includes(lease.auth.lease_id)) { client.leave(4003); throw deny(); }
      lease.client = client;
      lease.until = performance.now() + result.lease_seconds * 1000;
      this.state.players.get(client.sessionId).connected = true;
      this.electHost();
    }
    onLeave(client) {
      const lease = this.leases?.get(client.sessionId);
      if (!lease) return;
      pool.connections.set(lease.owner, Math.max(0, (pool.connections.get(lease.owner) || 1) - 1));
      if (!pool.connections.get(lease.owner)) pool.connections.delete(lease.owner);
      this.leases.delete(client.sessionId);
      this.state.players.delete(client.sessionId);
      this.electHost();
    }
    onDispose() {
      if (!pool.rooms.delete(this.roomId)) return;
      for (const lease of this.leases.values()) this.onLeave(lease.client);
      const owned = (pool.owned.get(this.owner) || 1) - 1;
      if (owned) pool.owned.set(this.owner, owned); else pool.owned.delete(this.owner);
    }
  };
}

export function installMatchmakingGuard(controller) {
  const invoke = controller.invokeMethod.bind(controller);
  const actions = { create: 'createRoom', joinOrCreate: 'quickMatch', joinById: 'joinRoom' };
  controller.exposedMethods = [...Object.keys(actions), 'reconnect'];
  controller.invokeMethod = (method, roomName, options, context) => {
    if (!context || !options || typeof options !== 'object' || Array.isArray(options)) throw deny();
    if (method === 'reconnect') return invoke(method, roomName, options, context);
    if (!actions[method] || (method !== 'joinById' && roomName !== 'universal')) throw deny();
    // This context is created by the HTTP controller, never from client options.
    return invoke(method, roomName, options, { ...context, platformAction: actions[method], platformRoomId: method === 'joinById' ? roomName : '' });
  };
}
