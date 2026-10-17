import { Client } from '@colyseus/sdk';
import { handshake } from './bridge.js';
import { createNetwork } from './session.js';

export const platformApi = 1;
export async function connect(options = {}) {
  let authorizer;
  if (options.developmentAuthorize) {
    if (!['localhost', '127.0.0.1'].includes(location.hostname)) throw new Error('本地开发授权提供器仅允许在 localhost 使用。');
    // This provider must obtain real one-use tickets from an authenticated LMS session.
    // The server never accepts a mock token or bypasses authorization in development.
    authorizer = { ticket: options.developmentAuthorize, close() {} };
  } else authorizer = await handshake(options);
  const network = createNetwork(Client, authorizer);
  window.addEventListener('pagehide', () => network.close().catch(() => {}), { once: true });
  return network;
}
export const GamePlatform = { connect, platformApi };
