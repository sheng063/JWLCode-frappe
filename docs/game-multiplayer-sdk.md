# HTML5 游戏通用联机接入：平台 SDK v1

适用范围：浏览器 HTML/ZIP 游戏、同一套长期运行的 UniversalRoom。新增游戏只上传前端产物和清单；游戏规则由客户端或房主客户端执行。

## 1. 快速开始

平台 SDK 源码位于 `packages/game-platform-client/`。构建后的 `game-platform.v1.js` 包含锁定的 Colyseus 客户端和沙箱内存存储适配。

```bash
npm --prefix services/game-runtime ci
python3 tools/build-colyseus-demo.py --release 1.0.0
```

输出在 `services/game-runtime/dist/`，包含通用 SDK、五子棋/赛车单 HTML 和 ZIP 模板。该命令只构建前端，不构建镜像。

模块方式：

```js
import { GamePlatform } from '../../packages/game-platform-client/index.js';
const net = await GamePlatform.connect();
const room = await net.quickMatch({ maxPlayers: 4 });
room.on('message', ({ from, type, payload }) => {
  // 按本游戏约定处理业务数据。
});
room.send('car:update', { x: 100, y: 200, angle: 1.57 });
```

相对路径按项目调整。使用 esbuild 时应用 `packages/game-platform-client/esbuild.js` 的 `colyseusSandboxStorage` 插件；参考 build-demo.js。它修复 Colyseus SDK 0.18.5 在 opaque iframe 内尝试使用 IndexedDB 的问题，不持久化登录信息或票据。

普通 script 方式：把生成的 SDK 和 index.html 一起放入 ZIP：

```html
<script src="./game-platform.v1.js"></script>
<script>
(async () => {
  const net = await GamePlatform.connect();
  const room = await net.createRoom({ maxPlayers: 2, visibility: 'private' });
  console.log('邀请房间号', room.roomCode);
})();
</script>
```

单 HTML 需把 SDK 构建代码内嵌，参照 dist/gomoku.html；不能只上传一个引用本地独立 JS 的 HTML。

## 2. 发布清单

ZIP 可在入口 HTML 同目录放 `game.manifest.json`；单 HTML 可通过教师上传表单生成清单，或在发布 API/CLI 中单独提供。

```json
{
  "manifestVersion": 1,
  "gameKey": "my-racing",
  "release": "1.0.0",
  "platformApi": "1",
  "client": { "entry": "index.html", "type": "zip" },
  "multiplayer": {
    "enabled": true,
    "mode": "relay",
    "compatibilityKey": "racing-protocol-v1",
    "minPlayers": 2,
    "maxPlayers": 4,
    "allowPrivateRoom": true,
    "allowQuickMatch": true
  }
}
```

- gameKey 在首次发布时固定到 Frappe 游戏记录，升级不能改成另一个游戏标识。
- 不填 compatibilityKey 时使用 release；默认不同版本不混房。显式共享兼容组后，所有对应客户端必须能理解彼此消息与快照。
- client.type 为 html 或 zip，入口必须与实际资源一致；ZIP 外层目录可正常识别。
- 人数范围 2–8；只允许平台已支持的 v1。清单不接受镜像、服务端入口、运行命令、任意后端 URL 或 CSP 白名单。
- 版本内容不可原地覆盖；升级使用新版本号。教师可通过“发布到”选择已有游戏。
- 不使用 SDK 的原单机 HTML/ZIP 不会自动获得多人能力，也不必启用联机选项。

## 3. 建房、匹配与加入

```js
const net = await GamePlatform.connect();
const room = await net.createRoom({ maxPlayers: 4, visibility: 'private' });
// 或 await net.quickMatch({ maxPlayers: 4 });
// 或 await net.joinRoom({ roomCode: 'AB12CD34' });
```

一个 net 同时只持有一个活动房间，切换前 await room.leave()。private 不参与自动匹配；房间号为邀请定位信息，加入者仍必须拥有同游戏、兼容组和范围的有效权限。quickMatch 只匹配 public 房间，人数设置不同也会分房。

room.id / room.roomCode 是房间号，room.playerId 是当前连接的玩家标识，room.hostId 是当前主持人，room.players 为平台玩家列表。玩家标识不包含邮箱或 LMS SID，不应跨房间用作持久账户 ID。

所有房间均为同一个 universal 类型的不同实例；游戏无需声明或注册专属 Room 类。

## 4. 事件

```js
const off = room.on('playerJoined', ({ playerId, label, connected }) => {});
room.on('playerLeft', ({ playerId }) => {});
room.on('playersChanged', ({ players, hostId }) => {});
room.on('playerConnectionChanged', ({ playerId, connected }) => {});
room.on('hostChanged', ({ hostId }) => {});
room.on('message', ({ from, type, payload, seq }) => {});
room.on('disconnected', ({ code, reconnecting }) => {});
room.on('reconnected', () => {});
room.on('roomClosed', ({ reason, code }) => {});
room.on('error', ({ code, message }) => {});
off();
```

on 返回取消订阅函数；onMessage(handler) 等价于 on('message', handler)。playerJoined 的新订阅会收到当前名单，hostChanged 的新订阅会收到当前主持人；playersChanged 在完整名单更新后触发，适合渲染或同步快照。

断网时暂保留名单并标记 disconnected，主持人可转交给仍在线的玩家；20 秒内有限重连会重新检查权限。重连成功保持当前玩家标识；整个页面刷新按新启动处理。网络中断期间 send 返回 false，不积压过期位置数据；已退出的房间 send 会抛错。

玩家正常离开、重连超时后发出 playerLeft。最后一人离开后释放房间。房间最长寿命默认 1 小时，超时关闭；运行进程崩溃时对局可以终止，不承诺恢复业务状态。

## 5. 消息协议

```js
room.send('piece:place', { x: 3, y: 5 });              // 其他在线玩家
room.send('board:snapshot', board, { to: playerId }); // 指定同房玩家
room.send('debug:echo', data, { echo: true });         // 包含自己
```

内部统一封装 protocol=1、type、payload、递增 seq。from 始终由服务端按真实连接注入，客户端伪造的 from 不生效。

type 使用 1–64 位字母、数字、冒号、下划线、短横线、点和斜线，不能使用保留的 platform:*。payload 必须为有限深度的 JSON 数据；不能发送二进制文件、图片、音频或视频流。当前 v1 仅使用可靠有序 WebSocket，不提供可选 UDP/不可靠策略。

单条完整消息不超过 16 KiB，默认每连接每秒最多 60 条。超限、非法系统命名空间、重复/倒退序号可能被断开；这些踢线不能通过重连绕过。资源文件仍走原游戏包资源路由。

服务器仅转发数据和维护名单，不解释坐标、棋盘、血量、回合、胜负或成绩。接收方需验证应用字段、处理顺序和冲突；客户端结果不具备反作弊或可信排行榜含义。

## 6. 快照与房主迁移

新成员加入时，由游戏发送当前业务快照。示例赛车由房主以 10Hz 广播位置，其他玩家发送输入并插值展示；示例五子棋由客户端交换落子，主持人同步棋盘。

hostChanged 只表示主持人选择结果，不包含赛车物理状态或棋盘。新房主应从自己保存的最近快照继续、暂停、重开或结束游戏。不要假设服务端保存了业务状态。

## 7. 本地开发模式

正常运行始终从 LMS 的隔离 iframe 使用 MessageChannel。开发时可把前端放在本机 Vite 服务，通过本地代理访问同一个已登录 LMS，提供 developmentAuthorize；仍须从真实 create_launch / issue_join_ticket 获取票据，服务器没有调试免登录或假票据开关。

```js
const net = await GamePlatform.connect({
  developmentAuthorize: async (action, options) => {
    // 由本地开发宿主用自己的 LMS 会话、CSRF token 和当前 launch_id 调用：
    return postToLocalLmsProxy('lms.lms.game_runtime.issue_join_ticket', {
      launch_id: launchId,
      action,
      room_id: options.roomCode || '',
      ...(options.maxPlayers ? { max_players: options.maxPlayers } : {}),
      ...(options.visibility ? { visibility: options.visibility } : {})
    });
  }
});
```

该提供器仅在 localhost / 127.0.0.1 可启用。开发父页的会话、CSRF token 不得编入游戏包；代理只在开发机使用。Runtime 的 GAME_ALLOWED_ORIGINS 须在平台开发环境配置时包含开发前端 origin，例如 http://localhost:5173；这属于平台配置，不随新增游戏修改。上传生产版本时使用默认 connect()。

## 8. 出错处理与实例限制

加入失败时显示错误并允许重试；操作票据只用一次，SDK 每次重试重新申请。错误房间号、满房、不同游戏或兼容组、被禁用账号/游戏/课程解锁变化均可使请求失败或在线连接断开。

默认平台限制 100 个房间、256 个连接、每用户 2 个在存房间/4 个连接；重连中的连接仍占用配额。实际容量需按游戏带宽、消息大小和在线人数压测，配置值不是承诺的 CCU。

[官方 Relay Room](https://docs.colyseus.io/room/relay) 提供中继模型背景；本平台用自有 UniversalRoom 加上 LMS 授权、隔离和限流。[部署与验收](game-colyseus.md) 说明当前实现及本地运行方式。
