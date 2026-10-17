# 通用 Room 重构验收（2026-10-17）

## 功能与回归

- Frappe 后端：15 项通用授权/发布 + 8 项原 Game + 10 项 ZIP + 13 项课程/课时权限，共 46 项通过。
- 前端：上传表单、操作桥接、游戏及学生解锁共 42 项通过；在隔离临时依赖环境运行，未改仓库依赖。
- Runtime/SDK：18 项通过，包含实际 HTTP/WS、站点/游戏/兼容组/范围隔离、满房、私房号、目标操作绑定、防重放、消息协议、主持人迁移、原生网络重连、主动踢线、配额及故障租约。
- 浏览器：两款游戏同时联机；五子棋落子、赛车客户端快照、房主迁移、私人邀请及跨游戏拒绝通过；撤销赛车后独立连接以 4003 断开，五子棋继续运行。
- 教师真实 UI：上传此前未注册的单 HTML、表单生成 manifest、直接建私房通过；验收临时游戏已删除。
- 四个临时学生账号已清理，两个示例学生开关恢复；本项目旧 per-game Runtime/Redis 栈已停用，独立外部容器未修改。
- 前端生产构建、站点迁移和本地部署通过；固定服务只注册 universal，无专用游戏 Room 或游戏 Redis。

## 零服务端更新证据

zero-server-update.json 对比教师 UI 上传、两款前端版本发布和联机验收前后的 Docker Image、容器 ID 和 StartedAt，全部相同。该阶段未修改 Runtime 源码（services/game-runtime/src/）、未构建或重启容器，也未增加代理路由。

## 本机小规模测量

以下是在独立测试 Runtime 中，以真实 HTTP/WS、模拟授权控制面、每玩家约 20Hz、每组约 1.5 秒的转发结果；不是生产压测或 CCU 承诺。字节数是应用层 JSON/envelope 计数，不包含 TCP/WebSocket/TLS 开销。

| 玩家 | 发出/投递 | 平均延迟 ms | P95 ms | Runtime RSS MiB | CPU ms | JSON 入/出 B |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 60/60 | 0.58 | 1.27 | 90.8 | 16.2 | 6870/7230 |
| 4 | 120/360 | 0.65 | 1.3 | 90.9 | 36.8 | 13711/43293 |
| 8 | 240/1680 | 0.81 | 1.82 | 94.1 | 49.2 | 27423/202041 |

真实本地部署另测 20 次回显往返：中位 2.8 ms，P95 4.1 ms。原始测量见 metrics.json / load-measurements.json。

## 记录

backend.log、frontend.log、runtime.log、browser.log、teacher-upload.log 保存验证输出。gomoku.png、race.png、mobile.png、teacher-upload.png 为真实浏览器截图。仅部署 localhost，公网 TLS、长期稳定性和 VPS 带宽容量需部署环境验证。
