import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { Server, matchMaker } from '@colyseus/core';
import { WebSocketTransport } from '@colyseus/ws-transport';
import { RedisPresence } from '@colyseus/redis-presence';
import { RedisDriver } from '@colyseus/redis-driver';
import { platformRoom } from './platform.js';
import { ControlPlane } from './control.js';

for (const key of ['GAME_DEPLOYMENT', 'GAME_RELEASE', 'GAME_ID', 'FRAPPE_URL', 'FRAPPE_SITE', 'GAME_SERVICE_KEY', 'GAME_REDIS_URL', 'GAME_MANIFEST']) {
  if (!process.env[key]) throw new Error(`Missing required configuration: ${key}`);
}
const manifest = JSON.parse(await readFile(process.env.GAME_MANIFEST, 'utf8'));
const { rooms } = await import(pathToFileURL(process.env.GAME_MODULE || new URL('./demo.js', import.meta.url).pathname).href);
const control = new ControlPlane({ url: process.env.FRAPPE_URL, site: process.env.FRAPPE_SITE, deployment: process.env.GAME_DEPLOYMENT, serviceKey: process.env.GAME_SERVICE_KEY });
const pool = { rooms: 0, connections: 0, seats: new Map(), draining: false };
const origins = new Set(['null', ...(process.env.GAME_ALLOWED_ORIGINS || '').split(',').filter(Boolean)]);
const presence = new RedisPresence(process.env.GAME_REDIS_URL);
const driver = new RedisDriver(process.env.GAME_REDIS_URL);
matchMaker.controller.DEFAULT_CORS_HEADERS = {
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Max-Age': '600', 'Vary': 'Origin',
};
matchMaker.controller.getCorsHeaders = headers => ({ 'Access-Control-Allow-Origin': origins.has(headers.get('origin')) ? headers.get('origin') : 'null' });
const transport = new WebSocketTransport({
  maxPayload: 16 * 1024,
  beforeUpgrade: request => {
    const origin = request.headers.get('origin');
    if (origin && !origins.has(origin)) return new Response('Origin denied', { status: 403 });
  },
});
const server = new Server({
  transport, presence, driver, greet: false, auth: false,
  express(app) {
    app.get('/healthz', (req, res) => res.json({ ok: true }));
    app.get('/readyz', async (req, res) => {
      try {
        const state = await control.call('service_status');
        await presence.get('runtime-health');
        pool.draining = state.status !== 'Ready';
        const ready = ['Ready', 'Starting'].includes(state.status);
        res.status(ready ? 200 : 503).json({ ready, deployment: process.env.GAME_DEPLOYMENT, release: process.env.GAME_RELEASE, rooms: pool.rooms, connections: pool.connections, status: state.status });
      } catch { res.status(503).json({ ready: false }); }
    });
  },
});
for (const room of manifest.rooms) {
  if (!rooms[room.key]) throw new Error(`Game module does not export room: ${room.key}`);
  server.define(room.key, platformRoom(rooms[room.key], { control, deployment: process.env.GAME_DEPLOYMENT, release: process.env.GAME_RELEASE, game: process.env.GAME_ID, room, pool, limits: manifest.limits })).filterBy(['platformScope']);
}
await server.listen(Number(process.env.PORT || 2567), '0.0.0.0');
const statusTimer = setInterval(async () => {
  try { pool.draining = (await control.call('service_status')).status !== 'Ready'; }
  catch { pool.draining = true; }
}, 3000);
statusTimer.unref();
server.onBeforeShutdown(() => { pool.draining = true; clearInterval(statusTimer); });
console.log(JSON.stringify({ event: 'runtime_ready', deployment: process.env.GAME_DEPLOYMENT, release: process.env.GAME_RELEASE }));
