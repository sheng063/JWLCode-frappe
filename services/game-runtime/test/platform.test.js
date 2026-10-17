import test from 'node:test';
import assert from 'node:assert/strict';
import { assertRoomAccess, validateEnvelope } from '../src/universal.js';
import { RelaySession } from '../../../packages/game-platform-client/session.js';

const auth = { site:'school', game:'game', game_key:'stable', compatibility_key:'v1', scope:'school', permissions:{minPlayers:2,maxPlayers:8,allowPrivateRoom:true,allowQuickMatch:true} };
const room = { isolation:JSON.stringify(['school','game','stable','v1','school']),maxClients:4,visibility:'private' };
test('all room joins enforce site/game/key/compatibility/scope and capacity permissions', () => {
  assertRoomAccess(room,auth);
  for (const key of ['site','game','game_key','compatibility_key','scope']) assert.throws(()=>assertRoomAccess(room,{...auth,[key]:'foreign'}));
  assert.throws(()=>assertRoomAccess(room,{...auth,permissions:{...auth.permissions,maxPlayers:2}}));
  assert.throws(()=>assertRoomAccess(room,{...auth,permissions:{...auth.permissions,allowPrivateRoom:false}}));
});
test('relay validates platform envelope while leaving game payload semantics alone', () => {
  const envelope = {protocol:1,type:'unknown-game:custom',seq:1,payload:{arbitrary:['data',42]},from:'spoofed'};
  assert.ok(validateEnvelope(envelope,-1,16384)>0);
  for(const patch of [{type:'platform:hostChanged'},{protocol:2},{seq:0},{payload:new Uint8Array(4)},{payload:{x:NaN}},{payload:'x'.repeat(16384)}]) assert.throws(()=>validateEnvelope({...envelope,...patch},0,16384));
});
test('SDK sends uniform envelopes and never exposes platform message namespace', () => {
  const sent=[];
  const signal=()=>{};
  const native={roomId:'AB123456',sessionId:'me',state:{players:new Map(),hostId:'me'},onStateChange:signal,onMessage:signal,onLeave:signal,send:(...args)=>sent.push(args),leave:async()=>4000};
  const sdk=new RelaySession(native);
  sdk.send('car:update',{x:42},{to:'peer'});
  assert.deepEqual(sent[0],['relay',{protocol:1,type:'car:update',payload:{x:42},seq:1,to:'peer'}]);
  assert.throws(()=>sdk.send('platform:fake',{}));
  assert.throws(()=>sdk.send('bytes','x'.repeat(17000)));
});
test('SDK roster and host events work for initial and changed members', () => {
  const signal=()=>{};
  const native={roomId:'AB123456',sessionId:'me',state:{players:new Map([['me',{label:'Me',connected:true}]]),hostId:'me'},onStateChange:signal,onMessage:signal,onLeave:signal};
  const sdk=new RelaySession(native),joined=[],left=[],hosts=[];
  sdk.on('playerJoined',x=>joined.push(x.playerId));sdk.on('playerLeft',x=>left.push(x.playerId));sdk.on('hostChanged',x=>hosts.push(x.hostId));
  native.state.players.set('peer',{label:'Peer',connected:true});sdk.updateRoster();
  native.state.players.delete('me');native.state.hostId='peer';sdk.updateRoster();
  assert.deepEqual(joined,['me','peer']);assert.deepEqual(left,['me']);assert.deepEqual(hosts,['me','peer']);
});
test('opaque iframe SDK storage never accesses browser persistence',async()=>{
  const {readFile}=await import('node:fs/promises');
  const html=await readFile(new URL('../dist/gomoku.html',import.meta.url),'utf8');
  assert.equal(html.includes('indexedDB.open'),false);
});
