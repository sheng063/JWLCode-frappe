/** Stable platform API v1; no game state lives here or on the relay server. */
export class RelaySession {
  constructor(native) {
    this.native = native;
    this.seq = 0;
    this.handlers = new Map();
    this.snapshot = new Map();
    this.previousHost = '';
    this.closed = false;
    this.connected = true;
    native.onStateChange(() => this.updateRoster());
    native.onMessage('relay', data => this.emit('message', data));
    native.onMessage('platform:roomClosed', data => this.emit('roomClosed', data));
    native.onDrop?.(() => { this.connected = false; this.emit('disconnected', { reconnecting: true }); });
    native.onReconnect?.(() => { this.connected = true; this.emit('reconnected', {}); });
    native.onError?.((code, message) => this.emit('error', { code, message }));
    native.onLeave(code => { this.closed = true; this.connected = false; if (code === 4004) this.emit('roomClosed', { code }); this.emit('disconnected', { code, reconnecting: false }); });
    this.updateRoster();
  }
  get id() { return this.native.roomId; }
  get roomCode() { return this.native.state?.roomCode || this.id; }
  get playerId() { return this.native.sessionId; }
  get players() { return [...this.snapshot.values()]; }
  get hostId() { return this.native.state?.hostId || ''; }
  on(event, listener) {
    if (typeof listener !== 'function') throw new TypeError('Event handler must be a function');
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event).add(listener);
    // Late subscribers get the current roster, without losing the initial join.
    if (event === 'playerJoined') for (const player of this.players) listener(player);
    if (event === 'hostChanged' && this.hostId) listener({ hostId: this.hostId });
    return () => this.handlers.get(event)?.delete(listener);
  }
  emit(event, payload) { for (const listener of this.handlers.get(event) || []) listener(payload); }
  updateRoster() {
    const current = new Map();
    this.native.state?.players?.forEach((player, id) => {
      const item = { playerId: id, label: player.label, connected: player.connected };
      current.set(id, item);
      if (!this.snapshot.has(id)) this.emit('playerJoined', item);
      else if (this.snapshot.get(id).connected !== item.connected) this.emit('playerConnectionChanged', item);
    });
    for (const [id, player] of this.snapshot) if (!current.has(id)) this.emit('playerLeft', player);
    this.snapshot = current;
    if (this.previousHost !== this.hostId) { this.previousHost = this.hostId; this.emit('hostChanged', { hostId: this.hostId }); }
    this.emit('playersChanged', { players: this.players, hostId: this.hostId });
  }
  send(type, payload, options = {}) {
    if (this.closed) throw new Error('房间已断开，请重新加入。');
    if (!this.connected) return false;
    if (payload === undefined) throw new Error('消息 payload 必须是 JSON 数据。');
    if (typeof type !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9:_.\/-]{0,63}$/.test(type) || type.startsWith('platform:')) throw new Error('消息类型无效或使用了保留命名空间。');
    const message = { protocol: 1, type, payload, seq: ++this.seq };
    if (options.to !== undefined) message.to = options.to;
    if (options.echo !== undefined) message.echo = options.echo;
    // JSON serializability is part of v1. Server independently validates size/depth.
    if (new TextEncoder().encode(JSON.stringify(message)).length > 16384) throw new Error('消息不能超过 16 KiB。');
    this.native.send('relay', message);
  }
  onMessage(listener) { return this.on('message', listener); }
  async leave() { this.closed = true; return this.native.leave(); }
}

export function createNetwork(Client, authorizer) {
  let active = null;
  let connecting = false;
  async function join(action, options = {}) {
    if (connecting || (active && !active.closed)) throw new Error('请先退出当前房间。');
    connecting = true;
    try {
      const ticket = await authorizer.ticket(action, options);
      const client = new Client(ticket.endpoint);
      client.http.options.credentials = 'omit';
      client.auth.token = ticket.ticket;
      const native = action === 'createRoom' ? await client.create('universal') :
        action === 'joinRoom' ? await client.joinById(ticket.room_id) : await client.joinOrCreate('universal');
      active = new RelaySession(native);
      return active;
    } catch (error) { throw new Error(error.message || '无法连接房间，请检查房间号或重新进入游戏。'); }
    finally { connecting = false; }
  }
  return {
    createRoom: options => join('createRoom', options),
    quickMatch: options => join('quickMatch', options),
    joinRoom: options => join('joinRoom', options),
    async close() { if (active && !active.closed) await active.leave(); authorizer.close?.(); },
  };
}
