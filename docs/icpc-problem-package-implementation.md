# ICPC package：当前实现与部署门槛

本次修改联动 JWLCode-frappe 与 JWLCode-judge-service，基础子集已完成真实跨服务验证，**不等于计划所有扩展及上线验收完成**。两侧启用开关默认关闭，不自动替换现有运行服务。更新日期：2026-09-06。

## 当前支持范围

- 私有 `.zip` / `.kpp` 上传，后台预检，报告、公开样例和鉴权 PDF 下载预览；确认草稿，事务发布。
- legacy 家族按受限子集检查，显式 legacy-icpc 可识别。无版本不会被标记为完整标准兼容。
- PDF 题面；必须有秘密数据、非空参考解文件和输入校验器文件。仅检查存在性，**不执行程序，不承诺完整规范验证**。
- 无公开样例、合法空输入/空答案；全部数据按原路径字典序固定，case ID 为去掉 `.in` 后的路径。
- 拒绝自定义/交互 checker、所有 validator_flags、2025-09、复杂数据分组、testdata.yaml、需要公开附件的包，以及未支持的显式执行限制。
- 只有 TeX 时报告阻止发布；转换器和程序验证沙箱尚未实现。
- 原包保持私有，版本内保存完整数据、manifest 和配置；学生只读题目投影及公开 PDF，不读取版本记录。`LMS Judge Test Case` 的新增版本字段为后续私有文件映射预留，目前包题的判题数据以版本记录为唯一来源。
- 手工题仍需样例及非空答案。包题投影禁止普通保存，只能发布新版本修改。
- 每次包题正式提交新建记录，固定版本、配置摘要、attempt。严格反馈不保存服务诊断或秘密输出；AC=100，其余=0。旧题保持教学反馈。
- 结果校验版本、attempt、请求 ID、case ID 和单调状态版本。AC 必须包含全部通过用例。

## 容量策略

原包 ≤20 MiB、展开总量 ≤64 MiB、单文件 ≤8 MiB、条目 ≤2000、压缩比 ≤200。测试总数 ≤100，每个输入/答案同时限制为 ≤256000 字符和 ≤256000 UTF-8 字节。拒绝符号链接、特殊文件、加密条目、路径穿越、重复路径及大小写冲突。只在内存读取，不解压到可执行目录，不递归展开归档。

YAML ≤64 KiB、深度 ≤20；安全解析、拒绝别名及重复键。时间由教师明确填写，范围 (0,30] 秒；内存范围 16000–1024000 KiB。包内 MiB 按 ×1024 转换，教师不能静默覆盖。倍率不作为秒数使用。

## Judge Service 已实现契约

`JWLCode-judge-service` 已实现该契约、独立默认比较器和 314 组官方参考工具差分。只有开启 `ICPC_ENABLED` 且验证记录匹配当前比较器文件 SHA-256 时才声明协议支持。所有非空 validator_flags 仍明确拒绝。

认证的 `GET /internal/v1/capabilities` 必须返回：

```json
{"protocols":["icpc-legacy-v1"],"icpc_default_comparator_verified":true}
```

其中 verified 由随包验证记录与比较器文件指纹计算，修改比较器后必须重新运行差分脚本生成记录。发布、运行和派发均检查能力；capabilities 还报告 min_memory_limit_kb，Frappe 会阻止发布低于部署内存下限的包。

现有 runs/judge-requests 请求增加 `protocol_version`、`comparison_mode=icpc_default`、空 `validator_flags`、`scoring_mode=icpc`、`package_version`、`config_digest`、稳定 `test_cases[].case_id`；正式请求另有 `attempt_id`。服务端拒绝未知协议；ICPC 路径不向 Judge0 传 expected_output，执行成功后再比较 stdout。结果及查询必须回传上述版本、摘要、attempt；cases 包含稳定 case_id，Accepted 用例状态使用 `Accepted`。服务端负责输出截断、编码错误及系统异常的正确分类。

## 迁移与回滚

1. 部署支持新旧协议的 Judge Service，确认其验证记录和实际执行限制，再开启服务端 ICPC_ENABLED。已有本地回归不替代目标部署环境的验证。
2. 部署本分支代码并安装新增 PyYAML 依赖，执行站点 `bench --site <site> migrate` 同步新增 DocType/字段，再构建前端。
3. 保持 `enable_icpc_problem_packages` 关闭，完成真实站点权限、文件下载、并发和端到端验收。
4. 使用站点配置 `enable_icpc_problem_packages = 1` 开启导入与发布。这个开关不会改变已经固定版本的提交。
5. 回滚时关闭该开关，保留表、原包、版本和提交，避免在队列运行中回滚为不认识版本字段的代码。自动切回旧指针和历史重判管理工具仍待实现。

未确认的导入 7 天后不允许确认；目前没有自动删除原包或配额回收任务。没有解包临时目录需要回收。部署前需补齐保留期/清理策略及用户存储配额。

## 验证与未完成项

- 独立解析测试可用 `python -m pytest lms/tests/test_problem_package.py`，无需 Frappe。
- Frappe 侧单测：`lms.tests.test_judge_service`、`lms.tests.test_problem_package_api`，与解析测试合计 41 项通过。新增 `lms.tests.test_problem_package_integration` 在真实 Frappe 17/MariaDB 上 5 项通过，覆盖空答案/无样例、幂等、版本冲突、学生权限、原包保护、签名/重复回调和终态防倒退。
- 修改的四个 Vue 组件经过 Vue compiler-sfc 脚本和模板编译检查。新增导入组件的 2 个交互测试在临时 Vite 7/Vitest 4/Vue 环境通过（API 客户端 mock）；现有表单全套回归仍受仓库依赖缺失影响。后端共 41 项单测通过，其中 Frappe 相关测试使用桩和 Mock。
- 仓库现有 Vitest 4 / Vite 5 组合启动报 `vite/module-runner` 未导出；测试运行器兼容性需要独立处理。
- 判题服务 31 项单测、314 组参考工具差分、7 项真实 Judge0 冒烟通过（C++/Python，AC/WA/CE/RE/TLE、空输出）。本机部署内存下限为 1024000 KiB，包题不会静默提高内存限制。
- `lms.tests.smoke_problem_package_pipeline.run` 已完成真实上传→预检→发布→提交→切换版本→Judge0→轮询应用结果，旧提交仍按旧版本得到 AC/100，隐藏数据不进入学生记录。测试使用内部临时服务与临时 SQLite，Frappe 测试数据均回滚。
- 本地已同步六个相关 DocType；运行中的正式服务代码和启用开关未切换。
- 待完成：真实题库包/浏览器全流程验收、目标部署环境验证、完整课程成绩/进度回归、存储配额与过期清理、回滚管理。版本冲突测试已覆盖顺序模拟，跨进程发布压力测试仍待补充。P5/P6 不在本次实现中。

规范依据：[legacy-icpc 官方规范](https://icpc.io/problem-package-format/spec/legacy-icpc.html)，核对日期 2026-09-05；规范 HTML 快照及 SHA-256 已保存在 `docs/reference/`；参考工具固定为 Kattis/problemtools 的 `4be848fc10fc74a9f604f2f31c62c64b70189fa5`。仍未执行包内程序，因此报告只使用“Structure checked; programs not executed”，不使用“标准包验证通过”。
