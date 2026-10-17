import { build } from 'esbuild';
import { colyseusSandboxStorage } from '../../packages/game-platform-client/esbuild.js';
import { mkdir, writeFile } from 'node:fs/promises';
const options = { bundle: true, plugins: [colyseusSandboxStorage], write: false, target: 'es2022', minify: true, nodePaths: ['./node_modules'] };
const shell = (title, script, board = false) => `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><style>*{box-sizing:border-box}body{margin:0;padding:20px;font:15px system-ui;background:#f0f4fa;color:#17243c}h1{font-size:24px}button,input{font:inherit;border:1px solid #cbd5e1;border-radius:8px;padding:8px;background:white}button{cursor:pointer}.controls{display:flex;gap:8px;flex-wrap:wrap}.controls input{max-width:140px}#status{min-height:42px}#players,#game-note{min-height:20px;color:#475569}#stage{height:50vh;min-height:250px;background:white;border:1px solid #cbd5e1;border-radius:16px;position:relative;overflow:hidden;touch-action:none;background-image:radial-gradient(#dbe3ed 1px,transparent 1px);background-size:24px 24px}.player{position:absolute;transform:translate(-50%,-50%);width:38px;height:38px;border-radius:50%;color:white;display:grid;place-items:center;font-size:12px;transition:left .1s,top .1s}#stage.board{display:grid;grid-template-columns:repeat(15,1fr);gap:0;background:#ead9af;width:min(100%,600px);height:auto;min-height:0;aspect-ratio:1;border-radius:8px}.cell{padding:0;border-radius:0;border:1px solid #c5b182;line-height:1;min-width:0;font-size:clamp(10px,3vw,25px);background:transparent}.cell[data-piece="1"]{color:#17243c}.cell[data-piece="2"]{color:white;text-shadow:0 0 2px #17243c}</style><h1>${title}</h1><p id="status">正在连接平台…</p><div class="controls"><button id="quick-match">快速匹配</button><button id="create-room">创建私人房间</button><input id="join-code" placeholder="输入房间号" aria-label="加入房间号"><button id="join-room">加入房间</button><button id="leave-room">退出房间</button><input id="room-code" readonly aria-label="当前房间号"></div><p id="players"></p><p id="game-note">${board ? '规则与棋盘均由客户端维护；此示例不提供反作弊。' : '点击场地或用方向键移动；房主客户端以 10Hz 广播位置快照。'}</p><div id="stage"></div>${script}</html>`;
await mkdir('dist', { recursive: true });
const globalSdk = await build({ ...options, entryPoints: ['../../packages/game-platform-client/index.js'], format: 'iife', globalName: 'GamePlatform' });
await writeFile('dist/game-platform.v1.js', globalSdk.outputFiles[0].text);
for (const [name, entry, title] of [['race','main.js','通用联机赛车实验室'],['gomoku','gomoku.js','通用联机五子棋']]) {
  const result = await build({ ...options, entryPoints: [`../../games/colyseus-demo/client/${entry}`], format: 'esm' });
  const script = result.outputFiles[0].text.replace(/<\/script/gi,'<\\/script');
  await mkdir(`dist/${name}`,{recursive:true});
  await writeFile(`dist/${name}/client.js`,script);
  await writeFile(`dist/${name}/index.html`,shell(title,'<script type="module" src="client.js"></script>',name==='gomoku'));
  await writeFile(`dist/${name}.html`,shell(title,`<script type="module">${script}</script>`,name==='gomoku'));
}
console.log('Built universal SDK, single HTML templates and ZIP client assets. No server image built.');
