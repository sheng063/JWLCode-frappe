# 编程编辑器

- 代码区工具栏从左到右提供格式化、设置和原有面板展开按钮。
- 编辑器主题可独立选择明亮 / 暗黑模式，位于字体选项上方；主题、字体和字号即时生效并保存在浏览器中。页面样式不再强制覆盖 Ace 的字号和主题背景。
- 设置弹窗只有“代码编辑器”和“键盘快捷键”两个菜单。设置即时生效，并以 `lms:programming-editor:v1` 保存在浏览器中。
- Python 使用 Black（88 列，标准四空格缩进），C++ 使用 clang-format（LLVM 风格，采用设置的缩进宽度）。格式化结果可撤销；请求期间修改了代码时不会用旧结果覆盖新内容。
- 安装 / 更新 LMS 的 Python 依赖后重启 Web 服务，才能使用格式化接口。新增依赖：`black~=25.1.0`、`clang-format~=19.1.7`。格式化不执行用户代码，单次最多 200 KB、10 秒，需登录。
- 提交记录从 `LMS Programming Exercise Submission` 查询，按题目及用户账号筛选；用户选择器显示姓名，实际使用唯一账号避免同名混淆。学生固定查询自己，服务端沿用 DocType 权限。
- 每次正式提交创建新记录；运行公开示例不写回历史提交。草稿按用户、题目、语言保存在当前浏览器。旧版本已覆盖的提交不能恢复。
- 快捷键：Ctrl / Cmd + Enter 运行，Ctrl / Cmd + Shift + Enter 提交，Alt + Shift + F 格式化，Alt + F 展开 / 还原代码面板。前两项可关闭。编辑器快捷键遵循所选 Standard / Vim / Emacs 模式。

## 验证

前端回归测试：`programmingEditorSettings.test.ts`、`programmingSubmissionFilters.test.ts`、`programmingExerciseEditor.test.ts`、`programmingExerciseRoute.test.ts`。
后端测试：`lms.tests.test_programming_editor`，需安装上述真实格式化工具。

### 字体、主题与快捷键浏览器验收（2026-09-07）

- 在 macOS Chrome 的实际 LMS 页面确认 Menlo、24px、明暗主题切换及刷新后的偏好恢复；检查计算样式，而非只检查 Ace 配置。
- 按设置列表顺序验证 Cmd+Enter 运行、Cmd+Shift+Enter 提交、Alt+Shift+F 格式化、Alt+F 展开 / 还原，以及 Tab、Shift+Tab、Cmd+/、Cmd+F、Cmd+Z、Cmd+Shift+Z。
- 切换至 C++ 后，Alt+Shift+F 通过真实服务完成格式化，重置仍保留 C++ 模板。
- A+B 练习实际运行通过 5 个公开样例；快捷键创建的提交最终为 Passed、100 分。关闭运行和提交开关后，两组快捷键均不发送请求。
- 相关 5 个前端测试文件共 14 项通过。宿主机现有 Vitest 4 / Vite 5 依赖不兼容，使用临时目录中的 Vitest 2.1.9 执行；生产构建使用运行容器现有依赖，通过。
