import { ServerError } from '@colyseus/core';

const denied = () => new ServerError(403, 'Game authorization denied');

export function platformRoom(GameRoom, { control, deployment, release, game, room, pool, limits }) {
  // The registered class owns lifecycle hooks: game code uses platform* hooks.
  for (const key of ['onCreate', 'onJoin', 'onLeave', 'onDrop', 'onReconnect', 'onDispose', 'onAuth']) {
    if (Object.hasOwn(GameRoom.prototype, key) || Object.hasOwn(GameRoom, key)) {
      throw new Error(`Use platform lifecycle hooks instead of ${key}`);
    }
  }
  return class AuthorizedRoom extends GameRoom {
    static async onAuth(token, options) {
      if (pool.draining || !/^[a-f0-9]{64}$/.test(token || '')) throw denied();
      const auth = await control.call('redeem_ticket', { ticket: token, room_key: room.key });
      if (auth.deployment !== deployment || auth.release !== release || auth.game !== game) throw denied();
      for (const [key, until] of pool.seats) if (until <= performance.now()) pool.seats.delete(key);
      if (pool.connections + pool.seats.size >= limits.maxConnections) throw new ServerError(429, 'Game server is full');
      pool.seats.set(auth.lease_id, performance.now() + 15000);
      // Overwrite all client-supplied partition keys before matchmaking.
      options.platformScope = auth.scope;
      return auth;
    }
    async onCreate(options) {
      if (pool.draining || pool.rooms >= limits.maxRooms) throw new ServerError(429, 'No room capacity');
      this._platformCounted = true;
      pool.rooms++;
      this.maxClients = room.maxClients;
      this.seatReservationTimeout = 10;
      this.maxMessagesPerSecond = 60;
      this.platformScope = options.platformScope;
      this._leases = new Map();
      this._refreshing = false;
      this.clock.setInterval(() => this.expireLeases(), 250);
      this.clock.setInterval(() => this.refreshLeases(), 5000);
      await this.platformCreate?.(options);
      await this.setPrivate(room.visibility === 'private');
    }
    async onJoin(client, options, auth) {
      if (!auth || auth.scope !== this.platformScope || auth.release !== release || auth.game !== game || auth.deployment !== deployment) throw denied();
      const renewed = await control.call('renew_leases', { lease_ids: [auth.lease_id] });
      if (!renewed.valid.includes(auth.lease_id)) throw denied();
      pool.seats.delete(auth.lease_id);
      if (pool.connections >= limits.maxConnections) throw new ServerError(429, 'Game server is full');
      pool.connections++;
      this._leases.set(client.sessionId, { client, auth, until: performance.now() + renewed.lease_seconds * 1000 });
      await this.platformJoin?.(client, options, auth);
    }
    expireLeases() {
      for (const lease of this._leases.values()) {
        if (lease.until <= performance.now()) lease.client.leave(4003, 'Game access expired');
      }
    }
    async refreshLeases() {
      if (this._refreshing || !this._leases.size) return;
      this._refreshing = true;
      try {
        const snapshot = [...this._leases.values()];
        for (let index = 0; index < snapshot.length; index += 100) {
          const batch = snapshot.slice(index, index + 100);
          const result = await control.call('renew_leases', { lease_ids: batch.map(x => x.auth.lease_id) });
          for (const lease of batch) {
            if (result.valid.includes(lease.auth.lease_id)) lease.until = performance.now() + result.lease_seconds * 1000;
            else { lease.until = 0; lease.client.leave(4003, 'Game access revoked'); }
          }
        }
      } catch { /* Never extend a lease on control-plane failure. */ }
      finally { this._refreshing = false; }
    }
    async onDrop(client) {
      const lease = this._leases.get(client.sessionId);
      if (!lease || lease.until <= performance.now()) return;
      try { await this.allowReconnection(client, 20); } catch { /* onLeave cleans up. */ }
    }
    async onReconnect(client) {
      const lease = this._leases.get(client.sessionId);
      if (!lease) { client.leave(4003); throw denied(); }
      const result = await control.call('renew_leases', { lease_ids: [lease.auth.lease_id] });
      if (!result.valid.includes(lease.auth.lease_id)) { client.leave(4003); throw denied(); }
      lease.client = client;
      lease.until = performance.now() + result.lease_seconds * 1000;
    }
    async onLeave(client, code) {
      if (this._leases?.delete(client.sessionId)) pool.connections--;
      await this.platformLeave?.(client, code);
    }
    async onDispose() {
      if (this._platformCounted) { pool.rooms--; this._platformCounted = false; }
      pool.connections -= this._leases?.size || 0;
      this._leases?.clear();
      await this.platformDispose?.();
    }
  };
}
