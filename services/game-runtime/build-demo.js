import { build } from 'esbuild';
import { colyseusSandboxStorage } from '../../packages/game-platform-client/esbuild.js';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
const result = await build({ entryPoints: ['../../games/colyseus-demo/client/main.js'], bundle: true, plugins: [colyseusSandboxStorage], write: false, format: 'esm', target: 'es2022', minify: true, nodePaths: ['./node_modules'] });
const script = result.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const html = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>联机移动实验室</title><style>*{box-sizing:border-box}body{margin:0;padding:24px;font:16px system-ui;background:#f0f4fa;color:#17243c}h1{font-size:24px}#status{min-height:48px;color:#475569}#stage{height:65vh;min-height:240px;background:white;border:1px solid #cbd5e1;border-radius:20px;position:relative;overflow:hidden;touch-action:none;background-image:radial-gradient(#dbe3ed 1px,transparent 1px);background-size:24px 24px}.player{position:absolute;transform:translate(-50%,-50%);width:44px;height:44px;border-radius:50%;color:white;display:grid;place-items:center;font-size:12px;transition:left .05s,top .05s;box-shadow:0 4px 12px #0002}</style><h1>联机移动实验室</h1><p id="status">正在申请联机授权…</p><div id="stage"></div><script type="module">${script}</script></html>`;
await mkdir('dist', { recursive: true });
await writeFile('dist/index.html', html);
console.log('Built dist/index.html');
