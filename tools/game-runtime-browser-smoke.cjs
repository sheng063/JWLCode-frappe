const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { Client } = require(path.resolve(__dirname,'../services/game-runtime/node_modules/@colyseus/sdk'));
const fixturePath=process.argv[2], output=process.argv[3], fixture=JSON.parse(fs.readFileSync(fixturePath));
const signal=path.dirname(fixturePath), base=process.env.LMS_URL || 'http://localhost:8000';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
 try{
  const pages=[],contexts=[],errors=[];
  for(let i=0;i<4;i++){
   const context=await browser.newContext();contexts.push(context);
   const account=fixture.accounts[i];
   assert.equal((await context.request.post(base+'/api/method/login',{form:{usr:account.user,pwd:account.password}})).status(),200);
   const page=await context.newPage();pages.push(page);page.on('pageerror',error=>errors.push(error.message));
   await page.goto(`${base}/lms/game/${i<2?fixture.gomoku:fixture.game}`);
   await page.frameLocator('iframe').locator('#status').filter({hasText:'联机已就绪'}).waitFor({timeout:25000});
   await page.frameLocator('iframe').locator('#quick-match').click();
  }
  const frame=i=>pages[i].frameLocator('iframe');
  for(let i=0;i<4;i++)await frame(i).locator('#status').filter({hasText:'2 人在线'}).waitFor({timeout:20000});
  const codes=await Promise.all(pages.map((p,i)=>frame(i).locator('#room-code').inputValue()));
  assert.equal(codes[0],codes[1]);assert.equal(codes[2],codes[3]);assert.notEqual(codes[0],codes[2]);
  await frame(0).locator('[data-cell="112"]').click();
  await frame(1).locator('[data-cell="112"][data-piece="1"]').waitFor();
  await frame(1).locator('[data-cell="113"]').click();
  await frame(0).locator('[data-cell="113"][data-piece="2"]').waitFor();
  console.log('PASS: single-HTML gomoku and ZIP racing run simultaneously in isolated rooms.');
  console.log('PASS: frontend gomoku moves synchronize through generic messages.');
  const before=await frame(3).locator('.player').evaluateAll(items=>items.map(x=>x.style.left));
  await frame(2).locator('#stage').click({position:{x:100,y:100}});
  await pages[2].waitForTimeout(350);
  const after=await frame(3).locator('.player').evaluateAll(items=>items.map(x=>x.style.left));
  assert.notDeepEqual(before,after);
  console.log('PASS: host-client racing snapshot reaches the other player.');
  await pages[2].setViewportSize({width:390,height:844});
  // The LMS may remount its route when switching between desktop/mobile layouts.
  await frame(2).locator('#status').waitFor();
  const mobileStatus=await frame(2).locator('#status').innerText();
  if(!mobileStatus.includes('已连接')){await frame(2).locator('#status').filter({hasText:'联机已就绪'}).waitFor();await frame(2).locator('#quick-match').click();}
  await frame(2).locator('#status').filter({hasText:'2 人在线'}).waitFor({timeout:20000});
  assert.equal(await pages[2].evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  await pages[2].screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  await pages[0].screenshot({path:path.join(output,'gomoku.png'),fullPage:true});
  await pages[3].screenshot({path:path.join(output,'race.png'),fullPage:true});
  // Whichever peer is now host, leaving one peer must make the other the host.
  await frame(2).locator('#leave-room').click();
  await frame(3).locator('#players').filter({hasText:'你（房主）'}).waitFor();
  console.log('PASS: host ownership transfers to a connected peer.');
  await frame(2).locator('#create-room').click();
  await frame(2).locator('#status').filter({hasText:'1 人在线'}).waitFor();
  const privateCode=await frame(2).locator('#room-code').inputValue();
  await frame(3).locator('#leave-room').click();
  await frame(3).locator('#join-code').fill(privateCode);await frame(3).locator('#join-room').click();
  await frame(2).locator('#status').filter({hasText:'2 人在线'}).waitFor();
  await frame(0).locator('#leave-room').click();
  await frame(0).locator('#join-code').fill(privateCode);await frame(0).locator('#join-room').click();
  await frame(0).locator('#status').filter({hasText:'another game or compatibility group'}).waitFor();
  console.log('PASS: room-code invitations work and cannot cross game identity.');
  await frame(0).locator('#quick-match').click();
  await frame(0).locator('#status').filter({hasText:'2 人在线'}).waitFor();
  async function api(page,method,body){return page.evaluate(async({method,body})=>{const r=await fetch('/api/method/'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.csrf_token},body:JSON.stringify(body)});if(!r.ok)throw new Error('API failed '+r.status);return(await r.json()).message;},{method,body});}
  const launch=await api(pages[2],'lms.lms.game_runtime.create_launch',{game:fixture.game});
  const ticket=await api(pages[2],'lms.lms.game_runtime.issue_join_ticket',{launch_id:launch.launch_id,action:'quickMatch',max_players:4});
  const native=new Client(ticket.endpoint);native.auth.token=ticket.ticket;native.http.options.credentials='omit';
  const direct=await native.joinOrCreate('universal');
  await assert.rejects(native.joinOrCreate('universal'));
  console.log('PASS: real LMS one-use ticket rejects replay.');
  const timings=[];
  direct.onMessage('relay',message=>{if(message.type==='probe:echo')timings.push(performance.now()-message.payload.sent);});
  for(let seq=1;seq<=20;seq++){direct.send('relay',{protocol:1,type:'probe:echo',payload:{sent:performance.now()},seq,echo:true});await sleep(50);}
  const end=Date.now()+3000;while(timings.length<20&&Date.now()<end)await sleep(50);
  assert.equal(timings.length,20);
  timings.sort((a,b)=>a-b);
  const health=await(await fetch(ticket.endpoint+'/readyz')).json();
  fs.writeFileSync(path.join(output,'metrics.json'),JSON.stringify({relayEchoRttMs:{samples:20,median:Number(timings[10].toFixed(2)),p95:Number(timings[18].toFixed(2))},health},null,2));
  const left=new Promise(resolve=>direct.onLeave(code=>resolve(code)));
  fs.writeFileSync(path.join(signal,'live.json'),JSON.stringify({ready:true}));
  const deadline=Date.now()+45000;while(!fs.existsSync(path.join(signal,'revoked'))&&Date.now()<deadline)await sleep(100);
  const code=await Promise.race([left,new Promise((_,reject)=>setTimeout(()=>reject(new Error('Lease revocation timed out')),32000).unref())]);
  assert.equal(code,4003);
  await pages[2].waitForFunction(()=>!document.querySelector('iframe'),null,{timeout:35000});
  assert.ok((await frame(0).locator('#status').innerText()).includes('2 人在线'),'revoking racing does not revoke gomoku');
  console.log('PASS: revocation closes independent WS (4003) and racing iframe; gomoku remains connected.');
  assert.deepEqual(errors,[]);
 }finally{await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
