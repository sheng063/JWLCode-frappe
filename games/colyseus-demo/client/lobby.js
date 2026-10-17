import { GamePlatform } from '../../../packages/game-platform-client/index.js';

export async function lobby({ maxPlayers, attach }) {
  const status = document.querySelector('#status');
  const code = document.querySelector('#room-code');
  let current;
  let detach = () => {};
  const net = await GamePlatform.connect();
  status.textContent = '联机已就绪，选择快速匹配或创建私人房间。';
  async function enter(action) {
    try {
      if (current && !current.closed) await current.leave();
      detach();
      status.textContent = '正在连接房间…';
      current = await action();
      const joined = current;
      code.value = current.roomCode;
      current.on('playersChanged', ({ players }) => {
        if (current !== joined) return;
        status.textContent = `已连接 · ${players.filter(x => x.connected).length} 人在线 · 房间 ${current.roomCode}`;
        code.value = current.roomCode;
        document.querySelector('#players').textContent = players.map(p => `${p.playerId === current.playerId ? '你' : p.label}${p.playerId === current.hostId ? '（房主）' : ''}${p.connected ? '' : '（重连中）'}`).join(' · ');
      });
      current.on('disconnected', ({ reconnecting }) => { if (current !== joined) return; status.textContent = reconnecting ? '网络已断开，正在尝试重连…' : '连接已结束，可重新匹配或加入。'; });
      current.on('reconnected', () => { status.textContent = '已重新连接，正在同步玩家…'; });
      current.on('roomClosed', () => { status.textContent = '房间已关闭，请重新创建或加入。'; });
      current.on('error', ({ message }) => { status.textContent = message || '连接失败，请重试。'; });
      detach = attach(current) || (() => {});
    } catch (error) { status.textContent = error.message || '连接失败，请重试。'; }
  }
  document.querySelector('#quick-match').onclick = () => enter(() => net.quickMatch({ maxPlayers }));
  document.querySelector('#create-room').onclick = () => enter(() => net.createRoom({ maxPlayers, visibility: 'private' }));
  document.querySelector('#join-room').onclick = () => enter(() => net.joinRoom({ roomCode: document.querySelector('#join-code').value.trim() }));
  document.querySelector('#leave-room').onclick = async () => { if (current) await current.leave(); detach(); code.value = ''; };
  return net;
}
