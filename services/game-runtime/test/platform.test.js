import test from 'node:test';
import assert from 'node:assert/strict';
import { platformRoom } from '../src/platform.js';

const auth = { lease_id: 'a'.repeat(64), deployment: 'dep', release: 'release', game: 'game', scope: 'school' };
function fixture(overrides = {}) {
  const pool = { rooms: 0, connections: 0, seats: new Map(), draining: false };
  const control = { call: async method => method === 'redeem_ticket' ? { ...auth } : { valid: [auth.lease_id], lease_seconds: 30 } };
  class Game { constructor() { this.clock = { setInterval() {} }; this.setPrivate = async () => {}; } }
  const Wrapped = platformRoom(Game, { control, pool, deployment: 'dep', release: 'release', game: 'game', room: { key: 'arena', maxClients: 4 }, limits: { maxConnections: 4, maxRooms: 2 }, ...overrides });
  return { Wrapped, pool, control };
}
test('static authentication rejects missing token and binds server-side scope', async () => {
  const { Wrapped } = fixture();
  await assert.rejects(Wrapped.onAuth('', {}));
  const options = { platformScope: 'attacker' };
  const result = await Wrapped.onAuth('f'.repeat(64), options);
  assert.equal(options.platformScope, 'school');
  assert.equal(result.game, 'game');
});
test('foreign deployment/release is rejected before matchmaking', async () => {
  const { Wrapped } = fixture({ control: { call: async () => ({ ...auth, release: 'foreign' }) } });
  await assert.rejects(Wrapped.onAuth('f'.repeat(64), {}));
});
test('room and connection quotas apply including outstanding reservations', async () => {
  const { Wrapped, pool } = fixture();
  pool.connections = 4;
  await assert.rejects(Wrapped.onAuth('f'.repeat(64), {}));
  pool.rooms = 2;
  await assert.rejects(new Wrapped().onCreate({ platformScope: 'school' }));
});
test('joinById cannot cross authorized room scope', async () => {
  const { Wrapped } = fixture();
  const room = new Wrapped();
  await room.onCreate({ platformScope: 'another-school' });
  await assert.rejects(room.onJoin({ sessionId: 'a' }, {}, auth));
});
test('lease failures never extend permission and expiration disconnects', async () => {
  const { Wrapped, control, pool } = fixture();
  const room = new Wrapped();
  await room.onCreate({ platformScope: 'school' });
  const leaves = [];
  const client = { sessionId: 'a', leave: code => leaves.push(code) };
  await room.onJoin(client, {}, auth);
  const lease = room._leases.get('a');
  const before = lease.until;
  control.call = async () => { throw new Error('offline'); };
  await room.refreshLeases();
  assert.equal(lease.until, before);
  lease.until = 0;
  room.expireLeases();
  assert.deepEqual(leaves, [4003]);
  await room.onLeave(client);
  await room.onDispose();
  assert.equal(pool.connections, 0);
  assert.equal(pool.rooms, 0);
});
test('revoked reconnect is rejected', async () => {
  const { Wrapped, control } = fixture();
  const room = new Wrapped();
  await room.onCreate({ platformScope: 'school' });
  const client = { sessionId: 'a', leave() {} };
  await room.onJoin(client, {}, auth);
  control.call = async () => ({ valid: [], lease_seconds: 30 });
  await assert.rejects(room.onReconnect(client));
});
test('game cannot override platform authorization lifecycle', () => {
  class Unsafe { onAuth() { return true; } }
  assert.throws(() => platformRoom(Unsafe, {}), /platform lifecycle/);
});
test('memory auth storage stays synchronous without browser persistence', async () => {
  const storage = await import('../../../packages/game-platform-client/storage.js');
  storage.setItem('test', 'value');
  let actual;
  storage.getItem('test', value => { actual = value; });
  assert.equal(actual, 'value');
  storage.removeItem('test');
  storage.getItem('test', value => { actual = value; });
  assert.equal(actual, undefined);
});
test('demo bundle avoids unavailable IndexedDB in opaque sandbox', async () => {
  const { readFile } = await import('node:fs/promises');
  const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8');
  assert.equal(html.includes('indexedDB.open'), false);
});
