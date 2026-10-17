import { Client } from '@colyseus/sdk';
import { handshake } from '../../../packages/game-platform-client/index.js';

const status = document.querySelector('#status');
const stage = document.querySelector('#stage');
let room;
const dots = new Map();
try {
  const platform = await handshake();
  const { client, roomType } = await platform.createColyseusClient(Client, 'arena');
  room = await client.joinOrCreate(roomType);
  room.onStateChange(state => {
    status.textContent = `已连接 · ${state.players.size} 人在线 · 点击场地或方向键移动`;
    const present = new Set();
    state.players.forEach((player, id) => {
      present.add(id);
      let dot = dots.get(id);
      if (!dot) { dot = document.createElement('div'); dot.className = 'player'; stage.append(dot); dots.set(id, dot); }
      dot.style.left = `${player.x}%`; dot.style.top = `${player.y}%`; dot.style.background = player.color;
      dot.textContent = id === room.sessionId ? '你' : player.id.slice(0, 4);
    });
    for (const [id, dot] of dots) if (!present.has(id)) { dot.remove(); dots.delete(id); }
  });
  room.onLeave(() => { status.textContent = '连接已结束，请通过上方“重新开始”再次进入。'; });
  room.onError(() => { status.textContent = '联机服务暂不可用，请重新开始。'; });
  const move = (x, y) => room.send('move', { x, y });
  window.addEventListener('keydown', event => {
    const directions = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    if (directions[event.key]) { event.preventDefault(); move(...directions[event.key]); }
  });
  stage.addEventListener('pointerdown', event => {
    const rect = stage.getBoundingClientRect();
    const player = room.state.players.get(room.sessionId);
    if (player) move((event.clientX - rect.left) / rect.width * 100 - player.x, (event.clientY - rect.top) / rect.height * 100 - player.y);
  });
  window.addEventListener('pagehide', () => { room.leave(); platform.close(); });
} catch (error) { status.textContent = error.message || '连接失败，请重新开始。'; }
