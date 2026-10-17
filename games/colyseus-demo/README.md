# Colyseus 游戏接入示例

客户端入口为 `client/main.js`，权威 Room 示例为 `services/game-runtime/src/demo.js`，构建模板为 `services/game-runtime/build-demo.js`。

在仓库根目录运行：

```bash
python3 tools/build-colyseus-demo.py --release 1.0.0
```

将生成的前端包、manifest 和不可变镜像 ID 交给 `tools/deploy-game.py`。完整命令见 [部署文档](../../docs/game-colyseus.md)。

客户端最小集成：

```js
import { Client } from '@colyseus/sdk';
import { handshake } from '../../packages/game-platform-client/index.js';
const platform = await handshake();
const { client, roomType } = await platform.createColyseusClient(Client, 'arena');
const room = await client.joinOrCreate(roomType);
```

示意中的相对路径须按实际客户端源文件位置调整。构建时应用 `colyseusSandboxStorage` 插件，确保 SDK 不访问沙箱禁止的持久存储。服务端导出 `{ rooms: { arena: MyRoom } }`，并采用 platform 生命周期钩子，使统一 Runtime 包装器持续掌管身份、租约与配额。
