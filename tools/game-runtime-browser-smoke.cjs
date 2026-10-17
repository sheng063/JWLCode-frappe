const fs = require('node:fs');
const path = require('node:path');
const fixturePath = process.argv[2];
const outputDir = process.argv[3];
const signalDir = path.dirname(fixturePath);
const baseUrl = process.env.LMS_URL || 'http://localhost:8000';
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fixture = JSON.parse(fs.readFileSync(fixturePath));
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_EXECUTABLE ? {executablePath:process.env.CHROMIUM_EXECUTABLE} : {})});
  const contexts = [];
  const pages = [];
  const failures = [];
  for (const account of fixture.accounts) {
    const context = await browser.newContext(); contexts.push(context);
    const r = await context.request.post(baseUrl+'/api/method/login',{form:{usr:account.user,pwd:account.password}});
    assert.equal(r.status(),200,'student login');
    const page = await context.newPage(); pages.push(page);
    page.on('pageerror', e => failures.push(e.message));
    page.on('console', m=> {if(m.type()==='error') console.log('browser error:',m.text().slice(0,350));});
    await page.goto(`${baseUrl}/lms/game/${fixture.game}`);
    await page.frameLocator('iframe').locator('#status').waitFor({timeout:20000});
    console.log('iframe status:',await page.frameLocator('iframe').locator('#status').innerText());
  }
  for (const page of pages) {
    await page.frameLocator('iframe').locator('#status').filter({hasText:'2 人在线'}).waitFor({timeout:20000});
    assert.equal(await page.frameLocator('iframe').locator('.player').count(),2);
  }
  const before = await pages[1].frameLocator('iframe').locator('.player').evaluateAll(nodes=>nodes.map(n=>n.style.left));
  const frame = pages[0].frames().find(f=>f.url().includes('/game-assets/'));
  await frame.locator('#stage').click({position:{x:100,y:100}});
  await pages[0].waitForTimeout(300);
  const after = await pages[1].frameLocator('iframe').locator('.player').evaluateAll(nodes=>nodes.map(n=>n.style.left));
  assert.notDeepEqual(before,after,'authoritative movement visible in the other browser');
  await pages[0].setViewportSize({width:390,height:844});
  await pages[0].frameLocator('iframe').locator('#status').filter({hasText:'2 人在线'}).waitFor({timeout:20000});
  assert.equal(await pages[0].evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth),true,'mobile page fits viewport');
  await pages[0].screenshot({path:path.join(outputDir,'mobile.png'),fullPage:true});
  await pages[1].screenshot({path:path.join(outputDir,'desktop.png'),fullPage:true});
  console.log('PASS: two different students share one room and synchronize movement.');
  const { Client } = require(path.resolve(__dirname,'../services/game-runtime/node_modules/@colyseus/sdk'));
  async function api(page, method, body) {
    return page.evaluate(async ({method,body})=>{
      const r=await fetch('/api/method/'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.csrf_token},body:JSON.stringify(body)});
      if(!r.ok) throw new Error('API failed: '+r.status);
      return (await r.json()).message;
    },{method,body});
  }
  const launch=await api(pages[0],'lms.lms.game_runtime.create_launch',{game:fixture.game});
  const ticket=await api(pages[0],'lms.lms.game_runtime.issue_join_ticket',{launch_id:launch.launch_id,room_key:'arena'});
  const directClient=new Client(ticket.endpoint);
  directClient.http.options.credentials='omit';directClient.auth.token=ticket.ticket;
  const directRoom=await directClient.joinOrCreate('arena');
  const replay=new Client(ticket.endpoint);replay.auth.token=ticket.ticket;
  await assert.rejects(replay.joinOrCreate('arena'));
  console.log('PASS: consumed join ticket cannot be replayed.');
  const disconnected=new Promise(resolve=>directRoom.onLeave(code=>resolve(code)));
  fs.writeFileSync(path.join(signalDir,'live.json'),JSON.stringify({game:fixture.game,connected:true}));
  // A signal file lets the host revoke game access while both browsers remain connected.
  const deadline=Date.now()+45000;
  while(!fs.existsSync(path.join(signalDir,'revoked')) && Date.now()<deadline) await pages[0].waitForTimeout(250);
  const code = await Promise.race([disconnected,new Promise((_,reject)=>setTimeout(()=>reject(new Error('Server lease did not revoke direct WebSocket')),32000).unref())]);
  assert.equal(code,4003);
  console.log('PASS: server revokes independent WebSocket with code 4003.');
  // Parent may remove the iframe first; direct server lease check is tested separately.
  await pages[0].waitForFunction(()=>!document.querySelector('iframe'),null,{timeout:35000});
  console.log('PASS: live game switch removes student iframe.');
  assert.deepEqual(failures,[]);
  await browser.close();
})().catch(error=>{console.error(error.stack);process.exitCode=1;setTimeout(()=>process.exit(1),1000)});
