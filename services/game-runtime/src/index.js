import { Server, matchMaker } from '@colyseus/core';
import { WebSocketTransport } from '@colyseus/ws-transport';
import { universalRoom, createPool, defaultLimits, installMatchmakingGuard } from './universal.js';
import { ControlPlane } from './control.js';

for (const name of ['FRAPPE_URL', 'FRAPPE_SITE', 'GAME_SERVICE_KEY']) if (!process.env[name]) throw new Error(`Missing configuration: ${name}`);
const control = new ControlPlane({ url: process.env.FRAPPE_URL, site: process.env.FRAPPE_SITE, serviceKey: process.env.GAME_SERVICE_KEY });
const limits = { ...defaultLimits };
for (const [key, env] of Object.entries({ maxRooms: 'GAME_MAX_ROOMS', maxConnections: 'GAME_MAX_CONNECTIONS', maxConnectionsPerUser: 'GAME_MAX_CONNECTIONS_PER_USER', maxRoomsPerUser: 'GAME_MAX_ROOMS_PER_USER', roomLifetimeSeconds: 'GAME_ROOM_LIFETIME_SECONDS' })) {
  if (process.env[env]) {
    const value = Number(process.env[env]);
    if (!Number.isSafeInteger(value) || value < 1) throw new Error(`Invalid configuration: ${env}`);
    limits[key] = value;
  }
}
const pool = createPool();
const startedAt = new Date().toISOString();
const origins = new Set(['null', ...(process.env.GAME_ALLOWED_ORIGINS || '').split(',').filter(Boolean)]);
installMatchmakingGuard(matchMaker.controller);
matchMaker.controller.DEFAULT_CORS_HEADERS = { 'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Max-Age': '600', Vary: 'Origin' };
matchMaker.controller.getCorsHeaders = headers => ({ 'Access-Control-Allow-Origin': origins.has(headers.get('origin')) ? headers.get('origin') : 'null' });
const transport = new WebSocketTransport({ maxPayload: 20 * 1024, beforeUpgrade(request) {
  const origin = request.headers.get('origin');
  if (origin && !origins.has(origin)) return new Response('Origin denied', { status: 403 });
} });
const updateStatus = async () => {
  try { const state = await control.call('service_status'); pool.accepting = state.status === 'Ready' && state.protocolVersion === 1; }
  catch { pool.accepting = false; }
};
await updateStatus();
const server = new Server({ transport, greet: false, auth: false, express(app) {
  app.get('/healthz', (req, res) => res.json({ ok: true }));
  app.get('/readyz', async (req, res) => {
    await updateStatus();
    res.status(pool.accepting ? 200 : 503).json({ ready: pool.accepting, roomTypes: ['universal'], protocolVersion: 1, startedAt, rooms: pool.rooms.size, connections: [...pool.connections.values()].reduce((a,b)=>a+b,0), forwarded: pool.forwarded, bytesIn: pool.bytesIn, bytesOut: pool.bytesOut, memoryBytes: process.memoryUsage().rss, cpu: process.cpuUsage() });
  });
} });
server.define('universal', universalRoom({ control, pool, limits })).filterBy(['partition']);
await server.listen(Number(process.env.PORT || 2567), '0.0.0.0');
const timer = setInterval(updateStatus, 3000);
timer.unref();
server.onBeforeShutdown(() => { pool.accepting = false; clearInterval(timer); });
console.log(JSON.stringify({ event: 'universal_runtime_ready', roomTypes: ['universal'], protocolVersion: 1, startedAt }));
