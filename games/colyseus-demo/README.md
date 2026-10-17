# 通用中继游戏示例（仅前端）

- `client/gomoku.js`：双人五子棋，客户端维护棋盘、回合和胜负，主持人同步快照。
- `client/main.js`：四人位置同步，房主客户端处理输入并以 10Hz 广播快照。
- `client/lobby.js`：两游戏共用的建房、快速匹配、房间号加入与事件界面。

没有游戏专属服务器或 Room。两款游戏都通过同一个长期运行的 universal 房间类型联机。

```bash
npm --prefix services/game-runtime ci
python3 tools/build-colyseus-demo.py --release 1.0.0
```

输出 SDK、单 HTML 和 ZIP 模板至 services/game-runtime/dist。脚本不构建镜像。

接口：

```js
import { GamePlatform } from '../../../packages/game-platform-client/index.js';
const net = await GamePlatform.connect();
const room = await net.createRoom({ maxPlayers: 4, visibility: 'private' });
room.on('message', ({ from, type, payload }) => {});
room.send('game:event', { value: 1 });
```

[统一 SDK 文档](../../docs/game-multiplayer-sdk.md) · [发布和部署](../../docs/game-colyseus.md)
