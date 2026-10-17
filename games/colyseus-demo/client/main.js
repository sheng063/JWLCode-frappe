import { lobby } from './lobby.js';

function attach(room) {
  const stage = document.querySelector('#stage');
  stage.innerHTML = '';
  const positions = new Map();
  const dots = new Map();
  function render() {
    for (const [id, position] of positions) {
      let dot = dots.get(id);
      if (!dot) { dot = document.createElement('div'); dot.className = 'player'; dot.dataset.player = id; stage.append(dot); dots.set(id, dot); }
      dot.style.left = `${position.x}%`; dot.style.top = `${position.y}%`;
      dot.style.background = id === room.playerId ? '#16a34a' : '#2563eb';
      dot.textContent = id === room.playerId ? '你' : id.slice(0, 4);
    }
    for (const [id, dot] of dots) if (!positions.has(id)) { dot.remove(); dots.delete(id); }
  }
  function reconcile() {
    for (const player of room.players) if (!positions.has(player.playerId)) positions.set(player.playerId, { x: 50, y: 50 });
    for (const id of positions.keys()) if (!room.players.some(p => p.playerId === id)) positions.delete(id);
    render();
  }
  function input(player, move) {
    if (room.hostId !== room.playerId || !Number.isFinite(move?.x) || !Number.isFinite(move?.y)) return;
    const old = positions.get(player);
    if (!old) return;
    positions.set(player, { x: Math.max(4, Math.min(96, old.x + Math.sign(move.x) * 3)), y: Math.max(4, Math.min(96, old.y + Math.sign(move.y) * 3)) });
    render();
  }
  const offRoster = room.on('playersChanged', reconcile);
  const offMessage = room.on('message', ({ from, type, payload }) => {
    if (type === 'car:input') input(from, payload);
    if (type === 'car:snapshot' && from === room.hostId && Array.isArray(payload)) {
      positions.clear();
      for (const [id, position] of payload) if (room.players.some(p => p.playerId === id) && Number.isFinite(position.x) && Number.isFinite(position.y)) positions.set(id, position);
      render();
    }
  });
  function move(x, y) { if (room.closed) return; if (room.hostId === room.playerId) input(room.playerId, { x, y }); else room.send('car:input', { x, y }, { to: room.hostId }); }
  const pointer = event => {
    const box = stage.getBoundingClientRect(), own = positions.get(room.playerId);
    if (own) move((event.clientX - box.left) / box.width * 100 - own.x, (event.clientY - box.top) / box.height * 100 - own.y);
  };
  const key = event => {
    const directions = { ArrowLeft: [-1,0], ArrowRight: [1,0], ArrowUp: [0,-1], ArrowDown: [0,1] };
    if (directions[event.key]) { event.preventDefault(); move(...directions[event.key]); }
  };
  stage.addEventListener('pointerdown', pointer);
  window.addEventListener('keydown', key);
  const timer = setInterval(() => { if (!room.closed && room.hostId === room.playerId) room.send('car:snapshot', [...positions]); }, 100);
  reconcile();
  return () => { clearInterval(timer); offRoster(); offMessage(); stage.removeEventListener('pointerdown', pointer); window.removeEventListener('keydown', key); };
}
lobby({ maxPlayers: 4, attach }).catch(error => { document.querySelector('#status').textContent = error.message; });
