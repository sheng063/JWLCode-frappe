# Game 通用 Colyseus 联机服务

本次重构按 [通用 Room 计划](game-colyseus-universal-room-plan.md) 实施，替代之前的每游戏权威服务器方案。当前为单实例、客户端规则、中继架构。

## 已实现的结构

- 一套固定的 UniversalRelay Runtime，只注册一个 `universal` 房间类型，各游戏/房间实例独立。
- Runtime 管理名单、房主、房间号、建房/快速匹配/定向加入、有限重连和 JSON 消息中继，不包含赛车或五子棋规则。
- 游戏仅交付 HTML/ZIP 和前端 manifest。教师从现有上传弹窗生成配置，或使用 CLI 发布；不构建游戏镜像、不新增容器/端口、不改代理、不重启 Runtime。
- 保留原静态上传、隔离 iframe、ZIP 资源 Cookie、教师试玩、课程/课时解锁与学生开关。联机 HTTP 使用短期票据且不携带 LMS Cookie。
- 固定服务使用 Colyseus 单进程本地 Presence/Driver，不再有游戏 Redis；Frappe 既有 Redis 的 game-runtime: 命名空间继续保存有 TTL 的 launch、一次性票据及租约。

## 本地运行结果

- 五子棋单 HTML：`http://localhost:8000/lms/game/ttnikv3v10`。
- 赛车 ZIP：`http://localhost:8000/lms/game/dl4h9o0lpe`，保留原示例游戏记录并升级其前端。
- 固定服务：`http://localhost:2572`；`/healthz` 检查进程，`/readyz` 检查授权控制面及单一 Room 类型。
- 两个示例均默认对学生关闭，教师可直接试玩；可在游戏库按需开放。
- 只部署本地环境。原独立 `colyseus-server:2567` 不属于本项目新服务，未修改。生产公网域名、证书和 TLS 未配置。

## 一次性部署平台

```bash
npm --prefix services/game-runtime ci
./docker/redeploy.sh
python3 tools/deploy-universal-runtime.py --port 2572
```

最后一个命令属于平台维护：构建固定 Runtime、配置唯一 endpoint/服务密钥，启动一组 Runtime+Nginx 容器。更新前若存在活动房间会拒绝执行。后续发布游戏不调用这个命令。

Runtime 使用 Node 22、锁定的 Colyseus 依赖、非 root、只读文件系统、CPU/内存限制。Nginx 处理 Upgrade、载荷限制与基础请求限流，私有 Node 端口不直接发布。默认只绑定 localhost；生产需在 HTTPS/WSS 入口后部署并按实际网络配置源站。

唯一服务配置保存于站点 `game_universal_runtime`，包含 endpoint、protocolVersion、服务状态和服务密钥。密钥通过临时私有文件交给 Bench，运行 env 位于已忽略的 `docker/.game-runtime/universal/runtime.env`，权限 0600。不要提交或分享 env 文件。

```bash
docker compose --env-file docker/.game-runtime/universal/runtime.env \
  -f docker/game-runtime.compose.yml logs --tail 100 runtime
```

日常游戏上传/激活只更新数据库及前端资源。Web 请求读取最新联机配置，不依赖重新启动 Frappe 才看见发布结果。

## 教师上传与版本升级

打开 Game → 上传游戏，选择 HTML/ZIP，勾选“启用通用联机”。可设置发行版本、稳定游戏标识、兼容联机组、最大人数、私人房间和快速匹配。选择“发布到”已有游戏即为前端升级；首次发布默认关闭学生访问。

ZIP 内的 game.manifest.json 优先使用；未提供时按表单生成。清单只能描述前端资源和 relay 配置，不接受游戏服务器目录、Node 启动命令、镜像、Compose 或任意后端 URL。普通静态 HTML/ZIP 不必启用此选项。

不同发行版本默认分房。显式共享 compatibilityKey 时允许混房，游戏作者需保证协议兼容。新 launch 固定到新资源，旧 launch 继续读取不可变旧资源；旧版本 Room 不因上传新游戏而被停止。单游戏开关仍同时约束该游戏的所有在线版本。

已发布的资源、游戏标识和协议不能原地改写。教师下载返回当前版本前端文件；删除逻辑游戏时清理关联版本资源。

## 开发者前端构建与发布

```bash
python3 tools/build-colyseus-demo.py --release 1.0.0
```

只生成 SDK、五子棋与赛车的单 HTML、ZIP 和 manifest，不操作 Docker。完整 SDK 契约见 [HTML5 游戏通用联机接入](game-multiplayer-sdk.md)。

```bash
python3 tools/deploy-game.py \
  --manifest services/game-runtime/dist/gomoku-html.manifest.json \
  --client services/game-runtime/dist/gomoku.html --title '联机五子棋'

python3 tools/deploy-game.py \
  --manifest services/game-runtime/dist/race-zip.manifest.json \
  --client services/game-runtime/dist/race.zip --title '联机赛车'
```

发布已有游戏时加 `--game '<Game ID>'` 并使用未发布的新版本号。该工具只将制品交给 Frappe 前端发布逻辑，不接收 --image/--port/--endpoint 参数，也不启动或重启联机服务。

## 鉴权和协议边界

1. GameDetail 调用 create_launch，使用现有 require_access / AccessEvaluator 检查登录、账号、全站/单游戏、课程/课时及个人规则。
2. launch 固定站点、用户/原会话、游戏、前端发行版本、兼容组和 scope。单 HTML 和 ZIP 都仅允许固定 Runtime 的连接源。
3. iframe 以随机 nonce 发 READY；父页只接受当前 Window，通过单独 MessageChannel 发出操作票据。重新开始、导航、撤权会关闭旧 launch/端口。
4. ticket 约 60 秒有效，一次性消费，绑定 createRoom/quickMatch/joinRoom 及目标房间号；操作或目标不一致时拒绝兑换。
5. 原生匹配控制器附加服务端操作上下文，UniversalRoom 从已兑换身份生成分房键。joinById 也检查 site/game/gameKey/compatibilityKey/scope 和 manifest 人数/可见性权限，不能凭房号绕过授权。
6. 已连接玩家每 5 秒批量复核，租约 30 秒。控制面不可用时不延长授权；撤权后服务端独立断开，前端 iframe 撤下并非唯一保障。教师保留试玩权限。
7. 游戏消息由同房中继直接转发，不经过 Python。服务端注入真实 from，校验 envelope、JSON/大小、顺序与速率；不判定业务胜负或可信分数。

默认 2–8 人、16 KiB/条、60 条/秒、单用户 2 个存续房间/4 个连接，房间寿命 1 小时。短暂断网可在 20 秒窗口重新验证后恢复；撤权和限流等主动踢线不允许借重连绕过。

## 迁移与保留数据

- 旧 `Colyseus` 运行模式在迁移中停用：原资源和旧发行记录保留、旧服务记录标为 Stopped，旧客户端不能自动变成新协议。
- 本地原示例已用同一 Game ID 上传新赛车 ZIP，其他静态游戏未改内容和访问规则。
- `LMS Game Release` 移除活跃模型中的 server_image/runtime_profile 字段，增加 client_type、filename、platform_api、compatibility_key。
- `LMS Game Deployment` 仅保留只读历史记录供追溯，不参与启动、授权、配置、发布或匹配，也不为新游戏创建记录。唯一服务由站点配置管理。
- 旧 per-game 容器需在无房间时停用。数据库迁移不擅自操作 Docker；本机本项目旧栈已停用，独立外部容器未处理。
- 老方案和老 QA 文件作为历史保留，当前行为以本文件及 SDK 文档为准。

## 验证与小规模测量

```bash
npm --prefix services/game-runtime test
```

Runtime 测试包含真实 HTTP/WS、同游戏多房、跨游戏/版本/范围/站点隔离、房号/满房、票据操作绑定、防重放、定向/广播/回显、消息限流、用户配额、房主交接、网络重连、故障租约及 2/4/8 人转发。

Frappe 回归模块：test_game_runtime、test_game、test_game_packages、test_game_access。前端覆盖新上传表单、桥接及原游戏/解锁界面。现有 Vite 5 与 Vitest 4 不兼容，相关前端测试在独立临时运行器完成，未改项目依赖。

真实浏览器验收：

```bash
python3 tools/test-game-runtime.py --game '<赛车 ZIP Game ID>' --gomoku '<五子棋 HTML Game ID>'
```

需可用 Playwright/Chromium，可用 PLAYWRIGHT_MODULE / CHROMIUM_EXECUTABLE 指向现有工具。验收创建 4 个临时学生，验证两游戏同时联机、落子/快照、房主交接、私房与跨游戏拒绝、票据重放、独立 WS 撤权及另一游戏继续运行；最后删账号并恢复游戏开关。

验收材料位于 [QA 目录](qa/game-universal-20261017/validation.md)，包含截图、日志、回环测量及容器镜像/启动时间不变的记录。测量仅代表本机小规模场景，不是生产容量或 CCU 承诺。

## 尚未承诺

多节点/热迁移、断电续局、反作弊、可信成绩、复杂好友/观战、跨房间业务状态不在此架构首期范围。业务规则、快照、主持人迁移后的继续/重开策略由各游戏客户端负责。生产 TLS、出站带宽与 VPS 容量需按部署环境和实际游戏另行配置、验证。
