# Apple Silicon 本地 Judge0 修复

2026-09-11 已部署并完成 Python/C++ 全链路验收。修复使用 ARM64 原生 isolate、Bash、Python 3.11、GCC 12 和 binutils；Judge0 Rails 服务继续使用原镜像。隔离机制和题目资源限制保持原设置。

## 验收

使用实际题目“正数四舍五入的实现”（`kg44c3uvm5`），通过已部署 LMS 的运行/提交接口、真实后台队列和认证回调：

| 语言 | 公开样例运行 | 完整提交 | 分数 | 最大内存 |
| --- | --- | --- | --- | --- |
| Python 3.11 | Accepted | 13/13 Passed | 100 | 7352 KB |
| C++ GCC 12 | Accepted | 13/13 Passed | 100 | 3184 KB |

题目内存限制为 131072 KB。测试提交已清理，没有手动注入评测结果。验收代码使用精确十进制处理，覆盖超出浮点数精度的大整数测试点。

详细结果见 [验收记录](qa/judge-native-e2e-20260911.json)，复验脚本为 `scripts/qa/verify_native_judge.py`（在本机 Frappe bench Python 环境执行，使用指定题目并在结束时删除自身创建的测试提交）。

## 部署

完整构建方案位于相邻 `JWLCode-judge-service` 仓库：`docker/arm64/Dockerfile`、`compose.arm64.yaml` 和 `docs/apple-silicon.md`。本机 `.env` 已启用该 Compose 覆盖配置，普通 Compose 重建会继续使用原生运行时镜像。先前只替换 isolate 的试验 Dockerfile 已由完整方案取代。

Docker Desktop 的 Rosetta 保持关闭；设置备份为同目录 `settings-store.before-lms-rosetta-20260909.json`。原始 isolate 的临时备份位于 `/tmp/lms-isolate-original-server` 和 `/tmp/lms-isolate-original-workers`。完整回退步骤见评测服务部署说明。
