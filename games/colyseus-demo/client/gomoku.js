import { lobby } from './lobby.js';

function attach(room) {
  const stage = document.querySelector('#stage');
  const note = document.querySelector('#game-note');
  stage.innerHTML = '';
  stage.classList.add('board');
  let board = Array(225).fill(0), turn = 0, finished = false;
  const cells = board.map((_, index) => {
    const cell = document.createElement('button'); cell.className = 'cell'; cell.dataset.cell = index; cell.setAttribute('aria-label', `棋格 ${index}`); stage.append(cell); return cell;
  });
  const playerOrder = () => room.players.map(p => p.playerId);
  function render() { cells.forEach((cell, i) => { cell.dataset.piece = board[i]; cell.textContent = board[i] ? '●' : ''; }); if (!finished) note.textContent = room.players.length < 2 ? '等待另一名玩家…' : `轮到${playerOrder()[turn % 2] === room.playerId ? '你' : '对方'}落子（客户端判定）`; }
  function apply(from, payload) {
    if (finished || room.players.length !== 2 || playerOrder()[turn % 2] !== from || !Number.isInteger(payload?.index) || payload.index < 0 || payload.index >= 225 || board[payload.index]) return;
    const color = turn % 2 + 1;
    board[payload.index] = color; turn++;
    const x = payload.index % 15, y = Math.floor(payload.index / 15);
    for (const [dx,dy] of [[1,0],[0,1],[1,1],[1,-1]]) {
      let count = 1;
      for (const sign of [-1,1]) for (let step = 1; step < 5; step++) {
        const xx = x + dx * step * sign, yy = y + dy * step * sign;
        if (xx < 0 || xx >= 15 || yy < 0 || yy >= 15 || board[yy*15+xx] !== color) break;
        count++;
      }
      if (count >= 5) { finished = true; note.textContent = `${color === 1 ? '黑' : '白'}方获胜（客户端判定，不作为可信成绩）`; }
    }
    render();
  }
  for (let i=0; i<cells.length; i++) cells[i].onclick = () => { if (room.closed || finished || playerOrder()[turn%2] !== room.playerId || board[i]) return; const before=turn; apply(room.playerId,{index:i}); if (turn !== before) room.send('piece:place',{index:i}); };
  const offMessage = room.onMessage(({ from, type, payload }) => {
    if (type === 'piece:place') apply(from, payload);
    if (type === 'board:snapshot' && from === room.hostId && Array.isArray(payload?.board) && payload.board.length === 225 && payload.board.every(x=>[0,1,2].includes(x)) && Number.isInteger(payload.turn)) { board = payload.board; turn = payload.turn; finished = !!payload.finished; render(); }
  });
  const offRoster = room.on('playersChanged', () => { render(); if (room.hostId === room.playerId) room.send('board:snapshot',{board,turn,finished}); });
  render();
  return () => { offMessage(); offRoster(); };
}
lobby({ maxPlayers: 2, attach }).catch(error => { document.querySelector('#status').textContent = error.message; });
