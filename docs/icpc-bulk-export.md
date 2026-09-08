# 编程练习批量导出

在 `/lms/programming-exercises` 勾选题目，点击选中工具栏的「批量导出」。后台完成后，浏览器下载 `programming-exercises.zip`。请求期间按钮显示进度状态，阻止重复提交；失败保留选中项并显示原因。

## ZIP 内容

- 每题一个独立 ZIP，内部为同名、小写字母及数字组成的根目录。
- `manifest.json` 对应题目 ID、标题、当前发布版本、独立 ZIP 文件名、SHA-256、LMS 判题配置和结构检查结果。
- `README.txt` 说明使用方法及验证范围。

保留原包的题面、数据、参考解、输入校验器、元数据及可执行权限。同名题不会覆盖，重复选择同一个 ID 只导出一次。平铺原包会补充标准根目录。包内原始文件字节保持不变。

采用与现有导入器一致的 [legacy-icpc 规范](https://icpc.io/problem-package-format/spec/legacy-icpc.html) 受限子集。保留原 `problem.yaml`，不将时间倍率改写为秒数；站点实际执行限制另外记录在清单中。只检查结构，不执行校验器或参考解，因此不宣称已通过完整程序验证。

## 限制与权限

`POST /api/method/lms.lms.problem_package.export.export_exercises`，JSON 参数 `{"exercises": ["题目ID"]}`，返回 `application/zip` 附件。

逐题检查 read/write/export 权限，再检查版本与导入记录的读取权限。普通学生及游客不能下载隐藏测试数据。最多 50 道题，原包累计及输出大小最多 100 MiB；每题沿用现有导入器的容量限制。失败时整批终止，不返回缺题的压缩包。只在内存打包，不创建公开文件。

手工题没有参考解和输入校验器，不能生成完整标准题包；严格模式会说明原因，要求先导入完整 ICPC 题包。不会生成虚假参考解、无条件通过的校验器，也不会把公开样例冒充秘密测试数据。

## 验证

- `lms/tests/test_problem_package_export.py`：8 项后端回归测试，可用安装了 Frappe 的 Python 执行 `python -m unittest lms.tests.test_problem_package_export`。
- `frontend/src/tests/exportProgrammingExercises.test.ts`：4 项下载测试，覆盖 CSRF、ZIP 响应、服务端错误及选择数量。
- 本地真实 Frappe/MariaDB 事务验证：导入并发布两道同名测试题，批量导出、逐包重检、二进制下载响应及游客拒绝；测试完成后回滚记录并清理私有测试文件。
- 仓库原有 Vite 5 / Vitest 4 不兼容，前端测试通过隔离 Vite 7 / Vitest 4 环境执行；未修改项目依赖。

- 本地站点已构建并部署；真实浏览器验证选中题目、中文批量导出按钮、POST 接口以及缺少题包的中文提示。接口兼容 Frappe 17 强制类型注解要求。
