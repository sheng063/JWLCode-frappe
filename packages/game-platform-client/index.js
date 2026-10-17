/** Browser-only startup helper. Colyseus Room APIs remain native. */
export async function handshake({ timeout = 15000 } = {}) {
  if (window.parent === window) throw new Error('请从 Game 页面打开此游戏。');
  const nonce = [...crypto.getRandomValues(new Uint8Array(16))].map(x => x.toString(16).padStart(2, '0')).join('');
  const port = await new Promise((resolve, reject) => {
    const ready = () => window.parent.postMessage({ type: 'jwl-game-ready', nonce }, '*');
    const listener = event => {
      if (event.source !== window.parent || event.data?.type !== 'jwl-game-connect' || event.data.nonce !== nonce || event.ports.length !== 1) return;
      cleanup(); resolve(event.ports[0]);
    };
    const interval = setInterval(ready, 250);
    const timer = setTimeout(() => { cleanup(); reject(new Error('Game 启动超时，请重新加载。')); }, timeout);
    const cleanup = () => { clearTimeout(timer); clearInterval(interval); window.removeEventListener('message', listener); };
    window.addEventListener('message', listener);
    ready();
  });
  const pending = new Map();
  port.onmessage = ({ data }) => {
    const waiter = pending.get(data?.id);
    if (!waiter || data.type !== 'ticket') return;
    pending.delete(data.id); clearTimeout(waiter.timer);
    if (data.error) waiter.reject(new Error(data.error)); else waiter.resolve(data.result);
  };
  port.start();
  return {
    ticket(roomKey) {
      if (pending.size) return Promise.reject(new Error('已有连接请求正在处理。'));
      const id = crypto.randomUUID();
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => { pending.delete(id); reject(new Error('联机授权请求超时。')); }, timeout);
        pending.set(id, { resolve, reject, timer });
        port.postMessage({ type: 'ticket', id, roomKey });
      });
    },
    async createColyseusClient(Client, roomKey) {
      const auth = await this.ticket(roomKey);
      const client = new Client(auth.endpoint);
      client.http.options.credentials = 'omit';
      client.auth.token = auth.ticket;
      return { client, roomType: auth.room_type };
    },
    close() { port.close(); for (const waiter of pending.values()) { clearTimeout(waiter.timer); waiter.reject(new Error('Game 已关闭。')); } pending.clear(); },
  };
}
