# Game 联机服务：Colyseus

实现日期：2026-10-17。对应设计：[接入方案](game-colyseus-plan.md)。

## 当前已实现

Frappe 提供游戏启动与访问授权，独立 Colyseus Runtime 负责房间和状态同步。当前交付单实例运行、版本化前端制品、独立 Redis/代理、可信本地发布工具、浏览器启动辅助库与双人示例。普通 HTML/ZIP 的上传、播放和学生解锁保留。

示例为“联机移动实验室”，点击场地或方向键移动；不同学生通过 Game 页面自动匹配并看到对方。游戏 ID 为本地部署生成值，不是跨站点固定标识。

本地验收部署：

- Game 页面：`http://localhost:8000/lms/game/dl4h9o0lpe`。
- Runtime：`http://localhost:2571`，健康检查 `/healthz`、就绪检查 `/readyz`。
- 当前示例版本：`1.0.3`；游戏默认对学生关闭，教师可以直接试玩，教师按需在游戏库开启。
- 本地原有 `colyseus-server:2567` 未修改。本服务使用独立 Compose 项目。
- 只部署本机测试环境，没有配置公网域名和生产 TLS。

## 服务与权限

`LMS Game.runtime_mode` 区分静态与 Colyseus 游戏；`active_release` 指向不可变制品记录。`LMS Game Release` 绑定前端 ZIP 校验值、入口、清单与服务端镜像 digest；`LMS Game Deployment` 登记 endpoint、Ready/Draining/Stopped 等状态。普通教师、学生不能通过通用 DocType API 发布服务器代码。

启动过程：

1. 已登录父页检查现有 Game 权限，创建与站点、用户、登录会话、游戏、版本、部署绑定的 launch。
2. iframe 平台库发起随机 nonce 握手。父页只接受当前 iframe，通过独立 MessageChannel 签发联机票据。
3. 原生 Colyseus SDK 用短期 ticket 发起匹配。Runtime 的强制静态 onAuth 通过服务身份到 Frappe 原子兑换；票据有效期 60 秒，只能成功消费一次。
4. 座位预订完成后直接 WSS/本地 WS 连入所属 Runtime；服务端核对房间 scope、游戏、版本和部署。
5. 连接每 5 秒批量复核权限，30 秒租约保证控制面不可用时不会无限保留操作权限。开关、课程/课时规则、账号、原会话、launch 关闭和部署停服均参与复核。

现阶段在线撤权依靠租约轮询，未实现设计中的服务端推送撤销事件；正常复核约 5 秒，故障兜底约 30 秒加事件循环调度。父页保留实时通知和 30 秒检查，但服务端踢线独立生效。

刷新、重新开始、离开页面或权限撤销会关闭旧 launch；断线重连窗口为 20 秒，服务端重新验证权限。重载整个页面按新启动处理，不保证恢复旧房间。

iframe 仍不使用 allow-same-origin。静态资源沿用 ZIP 专用 Cookie；联机 HTTP 明确使用 `credentials: omit` 和票据。CSP 只增加经站点配置批准的 Runtime HTTP(S)/WS(S) 源，通用 Frappe API 不向 null origin 开放。

Colyseus SDK 0.18.5 在构造 Client 时会尝试使用浏览器存储。模板通过构建插件将 SDK Storage 模块替换为内存实现，避免 opaque iframe 中的 IndexedDB 异常，票据不持久化。升级 SDK 后必须重新验证该构建适配。

## 本地构建和首次发布

前提：Docker、Python 3、Node >=22、npm；现有 `docker/docker-compose.yml` 的本地 Bench 已启动。发布操作通过受信 CLI 执行，没有公开的上传代码执行接口，也没有给 Frappe 挂载 Docker socket。

先把当前应用迁移和构建至本地：

```bash
./docker/redeploy.sh
```

构建示例（得到 client.zip、manifest 和不可变镜像 ID）：

```bash
python3 tools/build-colyseus-demo.py --release 1.0.0
```

发布新游戏，选择空闲端口：

```bash
python3 tools/deploy-game.py \
  --manifest services/game-runtime/dist/game.manifest.json \
  --client services/game-runtime/dist/client.zip \
  --image "$(docker image inspect jwlcode/game-runtime:colyseus-v1 --format '{{.Id}}')" \
  --port 2571 --title '联机移动实验室'
```

工具校验制品校验值与镜像一致性，登记版本、生成服务密钥、启动隔离的 Runtime/Redis/代理，检查候选版本 `/readyz`，再激活版本。返回 game/release/deployment ID、Game URL、Compose 项目名及本机 env 文件位置。

默认只监听 `127.0.0.1`，自动批准对应 localhost origin。构建/发布产物和密钥置于已忽略的 `docker/.game-runtime/`；runtime.env 权限为 0600，不应提交或分享。服务密钥通过临时文件传入 Bench，避免放进命令参数；站点配置按部署保存服务密钥。Web 请求读取最新联机配置，后续新增游戏无需重启 Frappe。

发布失败时停止候选部署并清理对应容器；保留发行记录供诊断，不自动删除游戏数据。工具当前自动检查 HTTP 就绪，完整真实联机验收需运行下方 smoke 工具，尚未接入 CI 的强制发布门禁。

## 后续游戏接入

1. 基于示例编写原生 Colyseus Room/Schema。游戏类使用 `platformCreate`、`platformJoin`、`platformLeave`、`platformDispose` 钩子；不要重写包装器管理的 onAuth/onCreate/onJoin/onDrop/onReconnect/onLeave/onDispose。
2. 服务端模块导出 `rooms` 映射，例如 `{ arena: MyRoom }`；镜像内通过 `GAME_MODULE=/app/game/rooms.js` 指向模块。以本项目 Runtime 镜像为基座时，将模块和游戏依赖构建进自己的镜像，保留统一入口。
3. 前端引入原生 SDK 和 `packages/game-platform-client/index.js`，调用 `handshake()`，然后 `createColyseusClient(Client, roomKey)`，继续使用原生 `joinOrCreate`/`joinById`、消息和状态接口。
4. 使用 `packages/game-platform-client/esbuild.js` 的 `colyseusSandboxStorage` 插件打包；其他打包器应提供等效的 SDK 内存存储别名。参考 `services/game-runtime/build-demo.js`。
5. 构建 client.zip 与自己的 OCI 镜像，按设计文档生成 manifest。运行通用 deploy-game 工具；无需改 Frappe 游戏页面和鉴权代码，也无需为单实例手写 Nginx 配置。

清单中的房间 visibility 必须为 public 或 private。public 允许已授权玩家自动匹配；private 房间不参与 joinOrCreate 搜索，需要游戏提供已授权的定向加入流程。两者都必须经过平台鉴权，房间 ID 不是入场凭证。

站点 scope 由服务端覆盖客户端选项，当前默认同站点、同游戏、同版本匹配；尚未提供班级范围配置或通用邀请大厅。游戏输入校验、胜负和权威状态仍由游戏作者实现。平台限制房间数、连接数、消息载荷和每秒消息数，并使用容器 CPU/内存限制。

## 升级、回滚和停服

升级使用更高 release，发布时传入原 game ID，并为新实例选择另一个端口：

```bash
python3 tools/build-colyseus-demo.py --release 1.0.1
python3 tools/deploy-game.py \
  --manifest services/game-runtime/dist/game.manifest.json \
  --client services/game-runtime/dist/client.zip \
  --image "$(docker image inspect jwlcode/game-runtime:colyseus-v1 --format '{{.Id}}')" \
  --port 2572 --game '<已有 Game ID>'
```

激活后新 launch 固定到新版本，旧启动上下文继续读取自己的前端资源；旧部署标记 Draining，停止新匹配，已有连接继续续租。原生 Room 不会在两个版本间透明迁移。教师下载返回当前版本 ZIP。

通过返回的 env 文件和项目名管理独立栈：

```bash
docker compose --env-file '<runtime.env>' -p '<project>' \
  -f docker/game-runtime.compose.yml logs --tail 100 runtime
```

旧房间结束后，由管理 CLI 调用 `lms.lms.game_publish.stop_deployment` 并 down 该栈。恢复保留版本时，先调用 `prepare_deployment` 标记 Starting，再用原 env 文件 up，检查 /readyz 后调用 `activate_release`。这些函数仅供 System Manager 的 Bench/可信发布 Worker 调用，没有 whitelisted HTTP 入口。

Compose 操作不会自动更改数据库部署状态；单独 down 会使就绪失败，现有客户端断线。生产环境应将这些步骤纳入发布 Worker，并增加排空截止时间、发布失败回滚与告警策略。

## 验证

Runtime：

```bash
npm --prefix services/game-runtime ci
npm --prefix services/game-runtime test
```

后端通过 Bench run-tests 运行 `lms.tests.test_game_runtime`、`lms.tests.test_game`、`lms.tests.test_game_packages`、`lms.tests.test_game_access`，共 41 项；前端相关 41 项通过。现有审计测试针对当前 Frappe 测试模式默认不生成 Version 的行为显式模拟生产模式，并为课时测试数据设置顺序，未修改原解锁业务规则。

真实浏览器验收：需安装可用 Playwright，必要时设置 PLAYWRIGHT_MODULE 和 CHROMIUM_EXECUTABLE 指向现有运行时。全站当前策略必须允许临时 QA 学生进入；工具不会更改全站权限规则。

```bash
python3 tools/test-game-runtime.py --game '<Game ID>'
```

工具创建两个临时学生，验证 iframe 运行、同房间状态与操作同步、票据重放拒绝、独立原生 WebSocket 的服务端撤权以及页面退出；结束后删除账号并恢复该游戏原开关。截图及日志输出至 QA 目录，不保存账号密码。

验收材料：[桌面](qa/game-colyseus-20261017/desktop.png)、[手机](qa/game-colyseus-20261017/mobile.png)、[浏览器日志](qa/game-colyseus-20261017/browser.log)。

## 尚未交付的后续能力

- 公网 TLS、生产域名/网络和生产容量规划；当前部署限定本机 localhost。
- 多进程池的命名空间和进程定向路由；当前每个部署一个 Node 实例和一套 Redis。
- 通用大厅、邀请码、班级匹配、服务器主动撤权事件。
- 对局成绩持久化、结果 outbox、崩溃续局、自动扩缩容及自动排空控制器。
- 托管任意用户上传的服务器源码；目前只发布受信开发者构建的镜像。

这些能力属于设计中的后续阶段，不影响当前单实例游戏按统一契约发布和运行。
