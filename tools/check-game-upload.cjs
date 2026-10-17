// Optional local UI acceptance check. Never contains a saved administrator password.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const base=process.env.LMS_URL||'http://localhost:8000',artifact=process.argv[2],out=process.argv[3];
if(!process.env.LMS_ADMIN_PASSWORD)throw new Error('Set LMS_ADMIN_PASSWORD for the local teacher upload check.');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
 const context=await browser.newContext();let page,created;
 const title='通用上传验收-'+Date.now();
 async function api(method,body){return page.evaluate(async({method,body})=>{const r=await fetch('/api/method/'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.csrf_token},body:JSON.stringify(body)});if(!r.ok)throw new Error('API rejected '+r.status);return(await r.json()).message;},{method,body});}
 try{
  assert.equal((await context.request.post(base+'/api/method/login',{form:{usr:process.env.LMS_ADMIN_USER||'Administrator',pwd:process.env.LMS_ADMIN_PASSWORD}})).status(),200);
  page=await context.newPage();await page.goto(base+'/lms/game');
  const help=page.locator('[data-testid="onboarding-help-modal"]');
  try { await help.waitFor({state:'visible',timeout:3000}); await help.locator(':scope > div').first().getByRole('button').last().click(); } catch {}
  await page.getByRole('button',{name:'上传游戏',exact:true}).click();
  await page.locator('.upload-name').fill(title);
  await page.getByLabel('启用通用联机').check();
  await page.getByLabel('发行版本',{exact:true}).fill('1.0.0');
  await page.getByLabel('最大联机人数').selectOption('2');
  await page.locator('#game-upload-form input[type=file]').setInputFiles({name:'teacher-relay.html',mimeType:'text/html',buffer:fs.readFileSync(artifact)});
  await page.screenshot({path:path.join(out,'teacher-upload.png'),fullPage:true});
  await page.locator('#game-upload-form').evaluate(form=>form.requestSubmit());
  const heading=page.locator('h2').filter({hasText:title});await heading.waitFor({timeout:20000});
  const games=await api('lms.lms.game.get_games',{});created=games.find(game=>game.title===title)?.name;
  assert.ok(created);assert.equal(games.find(game=>game.name===created).runtime_mode,'UniversalRelay');
  await heading.click();
  const frame=page.frameLocator('iframe');await frame.locator('#status').filter({hasText:'联机已就绪'}).waitFor({timeout:20000});
  await frame.locator('#create-room').click();await frame.locator('#status').filter({hasText:'1 人在线'}).waitFor();
  console.log('PASS: teacher uploads a new single HTML, generates manifest in UI, and joins a private universal room.');
  await frame.locator('#leave-room').click();
 }finally{
  try{
   if(page){
    if(!created){const games=await api('lms.lms.game.get_games',{});created=games.find(game=>game.title===title)?.name;}
    if(created)await api('lms.lms.game.delete_game',{name:created});
   }
  }finally{await browser.close();}
 }
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
