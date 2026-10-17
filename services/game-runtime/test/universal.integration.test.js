import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { randomBytes } from 'node:crypto';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { Client } from '@colyseus/sdk';

const tickets=new Map(), valid=new Set();
let stub,child,url, logs='',leaseSeconds=30,available=true;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(check,timeout=8000){const end=Date.now()+timeout;while(Date.now()<end){if(await check())return;await sleep(40);}throw new Error('Condition timed out: '+logs.slice(-1000));}
async function unusedPort(){const server=http.createServer();server.listen(0,'127.0.0.1');await once(server,'listening');const port=server.address().port;await new Promise(r=>server.close(r));return port;}
function issue({action='quickMatch',room_id='',game='game',compatibility_key='v1',scope='school',site='school',max_players=4,visibility=action==='quickMatch'?'public':'private',release='release-'+compatibility_key,player_id=randomBytes(8).toString('hex')}={}){
 const token=randomBytes(32).toString('hex'),lease_id=randomBytes(32).toString('hex');
 const auth={action,room_id,game,game_key:'key-'+game,compatibility_key,scope,site,max_players,visibility,player_id,lease_id,release,permissions:{minPlayers:2,maxPlayers:8,allowPrivateRoom:true,allowQuickMatch:true}};
 tickets.set(token,auth);valid.add(lease_id);return {token,auth};
}
async function connect(options={},override){const claim=issue(options);const client=new Client(url);client.auth.token=claim.token;const action=override||claim.auth.action;const room=action==='createRoom'?await client.create('universal'):action==='joinRoom'?await client.joinById(claim.auth.room_id):await client.joinOrCreate('universal');return {room,claim,client};}
before(async()=>{
 stub=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;
  const body=JSON.parse(raw||'{}');
  if(!available){res.writeHead(503).end();return;}
  if(req.headers['x-game-runtime']!=='universal'||req.headers['x-game-service-key']!=='k'.repeat(64)){res.writeHead(403).end();return;}
  let message;
  if(req.url.endsWith('service_status'))message={status:'Ready',protocolVersion:1};
  else if(req.url.endsWith('redeem_ticket')){
   const auth=tickets.get(body.ticket);
   if(!auth||auth.action!==body.action||auth.room_id!==body.room_id){res.writeHead(403).end();return;}
   tickets.delete(body.ticket);message={...auth,lease_seconds:leaseSeconds};
  }else if(req.url.endsWith('renew_leases'))message={valid:body.lease_ids.filter(id=>valid.has(id)),lease_seconds:leaseSeconds};
  else {res.writeHead(404).end();return;}
  res.setHeader('Content-Type','application/json');res.end(JSON.stringify({message}));
 });
 stub.listen(0,'127.0.0.1');await once(stub,'listening');
 const port=await unusedPort();url='http://127.0.0.1:'+port;
 child=spawn(process.execPath,['src/index.js'],{cwd:new URL('..',import.meta.url),env:{...process.env,PORT:String(port),FRAPPE_URL:'http://127.0.0.1:'+stub.address().port,FRAPPE_SITE:'school',GAME_SERVICE_KEY:'k'.repeat(64)}});
 child.stdout.on('data',x=>logs+=x);child.stderr.on('data',x=>logs+=x);
 await until(async()=>{try{return(await fetch(url+'/readyz')).ok;}catch{return false;}});
});
after(async()=>{child?.kill('SIGTERM');if(child?.exitCode===null)await once(child,'exit');await new Promise(r=>stub.close(r));});

test('single fixed room type serves unrelated games and multiple private rooms',async()=>{
 const a=await connect({game:'racing',action:'createRoom'}),b=await connect({game:'gomoku',action:'createRoom',max_players:2}),c=await connect({game:'racing',action:'createRoom'});
 assert.notEqual(a.room.roomId,c.room.roomId);assert.notEqual(a.room.roomId,b.room.roomId);
 const state=await(await fetch(url+'/readyz')).json();assert.deepEqual(state.roomTypes,['universal']);
 await Promise.all([a.room.leave(),b.room.leave(),c.room.leave()]);
});
test('quick matching partitions by game, compatible version, scope, site and room size',async()=>{
 const main=await connect({game:'match'}),peer=await connect({game:'match'}),other=[];
 assert.equal(main.room.roomId,peer.room.roomId);
 for(const options of [{game:'different'},{game:'match',compatibility_key:'v2'},{game:'match',scope:'classroom'},{game:'match',site:'other'},{game:'match',max_players:8}])other.push(await connect(options));
 for(const item of other)assert.notEqual(item.room.roomId,main.room.roomId);
 await Promise.all([main,peer,...other].map(x=>x.room.leave()));
});
test('room number joins enforce all identity partitions and reject unknown/full rooms',async()=>{
 const host=await connect({game:'private',action:'createRoom',max_players:2});
 for(const options of [{game:'foreign'},{game:'private',compatibility_key:'v2'},{game:'private',scope:'foreign'},{game:'private',site:'foreign'}])await assert.rejects(connect({...options,action:'joinRoom',room_id:host.room.roomId}));
 await assert.rejects(connect({game:'private',action:'joinRoom',room_id:'00000000'}));
 const peer=await connect({game:'private',action:'joinRoom',room_id:host.room.roomId});
 await assert.rejects(connect({game:'private',action:'joinRoom',room_id:host.room.roomId}));
 await Promise.all([host.room.leave(),peer.room.leave()]);
});
test('ticket cannot change action or target, be replayed, or bypass the single room registration',async()=>{
 const {token}=issue({action:'createRoom'}),client=new Client(url);client.auth.token=token;
 await assert.rejects(client.joinOrCreate('universal'));
 const room=await client.create('universal');
 await assert.rejects(client.create('universal'));
 await assert.rejects(new Client(url).create('racing'));
 await assert.rejects(new Client(url).joinById(room.roomId));
 await room.leave();
});
test('relay supports arbitrary game types, server sender ID, targets and default no echo',async()=>{
 const a=await connect({game:'relay'}),b=await connect({game:'relay'}),c=await connect({game:'relay'});
 const receivedA=[],receivedB=[],receivedC=[];
 a.room.onMessage('relay',m=>receivedA.push(m));b.room.onMessage('relay',m=>receivedB.push(m));c.room.onMessage('relay',m=>receivedC.push(m));
 a.room.send('relay',{protocol:1,type:'new-game:unknown',payload:{hello:'world'},seq:1,from:'spoof'});
 await until(()=>receivedB.length===1&&receivedC.length===1);
 assert.equal(receivedB[0].from,a.room.sessionId);assert.equal(receivedA.length,0);
 a.room.send('relay',{protocol:1,type:'private:snapshot',payload:{snapshot:true},seq:2,to:b.room.sessionId});
 await until(()=>receivedB.length===2);assert.equal(receivedC.length,1);
 a.room.send('relay',{protocol:1,type:'echo',payload:null,seq:3,echo:true});await until(()=>receivedA.length===1);
 await Promise.all([a,b,c].map(x=>x.room.leave()));
});
test('reserved system namespace and oversized message close offending peers',async()=>{
 for(const message of [{type:'platform:hostChanged',payload:{},seq:1},{type:'big',payload:'x'.repeat(17000),seq:1}]){
  const {room}=await connect({game:'bad-message'});const left=new Promise(resolve=>room.onLeave(code=>resolve(code)));
  room.send('relay',{protocol:1,...message});assert.equal(await left,4008);
 }
});
test('host leave elects next connected peer and empty rooms are released',async()=>{
 const a=await connect({game:'host'}),b=await connect({game:'host'});
 await until(()=>b.room.state.hostId===a.room.sessionId);
 await a.room.leave();await until(()=>b.room.state.hostId===b.room.sessionId);
 await b.room.leave();await until(async()=>((await(await fetch(url+'/readyz')).json()).rooms===0));
});
test('short authorization lease expires while control plane is unreachable',async()=>{
 leaseSeconds=0.6;
 const {room}=await connect({game:'lease'});const left=new Promise(resolve=>room.onLeave(code=>resolve(code)));
 available=false;
 try{assert.equal(await left,4003);}finally{available=true;leaseSeconds=30;await fetch(url+'/readyz');}
});
test('2/4/8 player rooms relay at 20Hz with measured latency and resource counters',async()=>{
 const measurements=[];
 for(const count of [2,4,8]){
  const peers=[],latencies=[];
  for(let i=0;i<count;i++)peers.push(await connect({game:'load-'+count,max_players:count}));
  const before=await(await fetch(url+'/readyz')).json(),start=performance.now();
  const received=peers.map(()=>0);
  peers.forEach((peer,index)=>peer.room.onMessage('relay',message=>{received[index]++;latencies.push(performance.now()-message.payload.sent);}));
  for(let seq=1;seq<=30;seq++){
   for(const peer of peers)peer.room.send('relay',{protocol:1,type:'load:tick',payload:{sent:performance.now(),sample:'123456789012345678901234567890'},seq});
   await sleep(50);
  }
  await until(()=>received.every(value=>value===30*(count-1)));
  const elapsedMs=performance.now()-start,after=await(await fetch(url+'/readyz')).json();
  latencies.sort((a,b)=>a-b);
  measurements.push({players:count,hzPerPlayer:20,sent:count*30,delivered:received.reduce((a,b)=>a+b),elapsedMs:Math.round(elapsedMs),averageMs:Number((latencies.reduce((a,b)=>a+b)/latencies.length).toFixed(2)),p95Ms:Number(latencies[Math.floor(latencies.length*.95)].toFixed(2)),runtimeRssBytes:after.memoryBytes,cpuMs:(after.cpu.user+after.cpu.system-before.cpu.user-before.cpu.system)/1000,jsonBytesIn:after.bytesIn-before.bytesIn,jsonBytesOut:after.bytesOut-before.bytesOut});
  await Promise.all(peers.map(x=>x.room.leave()));
 }
 console.log('Relay smoke load measurements:',JSON.stringify(measurements));
});
test('per-user room and connection quotas prevent unlimited creation',async()=>{
 const owner='owner-'+randomBytes(4).toString('hex');
 const a=await connect({game:'quota-rooms',action:'createRoom',player_id:owner}),b=await connect({game:'quota-rooms',action:'createRoom',player_id:owner});
 await assert.rejects(connect({game:'quota-rooms',action:'createRoom',player_id:owner}));
 await Promise.all([a.room.leave(),b.room.leave()]);
 const member='member-'+randomBytes(4).toString('hex'), peers=[];
 for(let i=0;i<4;i++)peers.push(await connect({game:'quota-connections',max_players:8,player_id:member}));
 await assert.rejects(connect({game:'quota-connections',max_players:8,player_id:member}));
 await Promise.all(peers.map(x=>x.room.leave()));
});
test('native network reconnection preserves member ID and revalidates the lease',async()=>{
 const a=await connect({game:'reconnect'}),b=await connect({game:'reconnect'}),original=a.room.sessionId;
 const reconnected=new Promise(resolve=>a.room.onReconnect(()=>resolve(true)));
 a.room.reconnection.minUptime=0;
 a.room.connection.transport.close(4010, 'simulate network retry');
 await Promise.race([reconnected,sleep(8000).then(()=>{throw new Error('Reconnect timed out');})]);
 assert.equal(a.room.sessionId,original);
 await until(()=>b.room.state.players.get(original)?.connected===true);
 await Promise.all([a.room.leave(),b.room.leave()]);
});
test('excessive message frequency disconnects the offender',async()=>{
 const {room}=await connect({game:'rate'}),left=new Promise(resolve=>room.onLeave(code=>resolve(code)));
 for(let seq=1;seq<=100;seq++)room.send('relay',{protocol:1,type:'rate:test',payload:null,seq});
 assert.ok((await left)>=4000);
});

test('explicit compatibility group permits two front-end release versions to share a room',async()=>{
 const a=await connect({game:'compatible',release:'front-1'}),b=await connect({game:'compatible',release:'front-2'});
 assert.equal(a.room.roomId,b.room.roomId);
 await Promise.all([a.room.leave(),b.room.leave()]);
});
