import { Room } from '@colyseus/core';
import { Schema, MapSchema, defineTypes } from '@colyseus/schema';

class Player extends Schema {
  constructor(id) { super(); this.id = id; this.x = 50; this.y = 50; this.color = '#2563eb'; }
}
defineTypes(Player, { id: 'string', x: 'number', y: 'number', color: 'string' });
class State extends Schema { constructor() { super(); this.players = new MapSchema(); } }
defineTypes(State, { players: { map: Player } });

export class DemoRoom extends Room {
  platformCreate() {
    this.setState(new State());
    this.patchRate = 50;
    const messages = new Map();
    this.onMessage('move', (client, input) => {
      if (!input || !Number.isFinite(input.x) || !Number.isFinite(input.y)) return;
      const now = performance.now();
      if (now - (messages.get(client.sessionId) || 0) < 40) return;
      messages.set(client.sessionId, now);
      const player = this.state.players.get(client.sessionId);
      if (player) {
        player.x = Math.max(3, Math.min(97, player.x + Math.sign(input.x) * 2));
        player.y = Math.max(3, Math.min(97, player.y + Math.sign(input.y) * 2));
      }
    });
    this.platformMessages = messages;
  }
  platformJoin(client, options, auth) {
    const player = new Player(auth.player_id.slice(0, 8));
    player.color = ['#2563eb', '#ea580c', '#16a34a', '#9333ea'][this.clients.length % 4];
    this.state.players.set(client.sessionId, player);
  }
  platformLeave(client) {
    this.platformMessages.delete(client.sessionId);
    this.state.players.delete(client.sessionId);
  }
}
export const rooms = { arena: DemoRoom };
