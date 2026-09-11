# 课程导入导出审计（2026-09-08）

## 结论

当前课程 ZIP 并非只有课程文本和题号。正文 EditorJS `program` 块引用的普通编程题会导出完整题目记录及测试用例，导入时先创建题目，再创建课时。普通题在目标系统不存在的场景已通过真实数据库测试，不需要提前导入。

课程引用保存的是题目的内部 `name`，不是界面上的 `exercise_number`（P-000xxx）。普通题跨目标导入会生成新内部 ID 和新显示编号。缺失题目的课程仍可导入并保留原内部 ID；之后新建同名题不会自动修复关联。恢复完全相同的内部 ID 可以让引用重新有效，或应手动重新选择题目。独立 ICPC 导入一般会新建目标题目，因此不能依靠相同标题或显示编号恢复课程引用。

ICPC 题不具备完整的课程 ZIP 迁移支持。课程 ZIP 包含其题目记录和 `active_package_version` 引用，但没有打包对应版本、题面文件及隐藏测试数据。目标不存在原题时，导入报错 `Package settings require the import service.`。先通过独立题目包入口导入题目并不能保证解决：课程导入按源内部 ID 判断是否已存在，不按标题/显示编号判断。需要正式实现 ID 映射与题目包迁移，或调整课程中的引用和包内容。

## 环境与方法

- 仓库：`JWLCode-frappe`；运行站点：本地 Docker `jwl-learning-frappe-1` / `school.localhost`。
- 仓库与运行环境的 `course_import_export.py` SHA-256 一致：`182b6dd6d64f71bd5e55ff2aa0d198b8ee14815d95c089c38b4d79a609850ee6`。
- 后端：真实 Frappe/MariaDB 调用导入导出 API 函数，实际创建 ZIP、读写临时文档；仅 mock 导出文件的延迟删除队列。每项测试回滚数据库，清理本测试前缀的文件。
- “目标不存在”通过移除当前事务内创建的源测试题来模拟；ICPC 使用现有题只读导出的记录，并将包内题目 ID 改为不存在的测试 ID，验证创建路径；不是独立全新站点迁移。
- 前端：实际组件测试和下载工具测试，网络以 mock 隔离；另执行真实 Chrome 上传/导入验证，浏览器临时课程和上传包单独清理。
- 未修改业务实现；新增审计脚本、导出前端测试和本报告。用户原有改动未覆盖。

## 测试结果

后端 **31 项：21 通过，8 个断言失败，2 个异常错误**。其中 4 项是原有内容健壮性测试，27 项为此次场景审计。失败断言按应保留的迁移语义编写，未使用 expectedFailure 隐藏问题。

前端 **12 项全部通过**：原有导入表单 8 项，新增导出下载 4 项。仓库默认 `npm test` 由于 Vitest 4.1.11 / Vite 5.0.11 不兼容，在启动时报告 `ERR_PACKAGE_PATH_NOT_EXPORTED: vite/module-runner`；测试使用已有 `/tmp/lms-editor-test-runtime` 的 Vitest 2.1.9 / jsdom 26 环境完成，未修改项目依赖。

| 编号 | 场景 | 结果 |
| --- | --- | --- |
| 原有 4 项 | 非 JSON 内容、非对象 JSON、畸形块容错 | 通过 |
| 01 | 中文正文、章节/课时结构、顺序学习设置往返 | 通过 |
| 02 | 导出包含普通题题面、题目记录、输入输出用例 | 通过 |
| 03 | 普通题在目标不存在时随课程创建 | 通过，内部 ID 和显示编号均改变 |
| 04 | 原题仍存在时同站导入 | 通过，复用原题 |
| 05 | 缺失编程题引用 | 通过，允许导入并保留悬空 ID |
| 06 | 后续新建同名题 | 通过验证：不会自动关联 |
| 07 | 后续恢复完全相同内部 ID | 通过验证：引用可解析 |
| 08 | 纯文本课程重复导入 | 通过，每次创建新课程 |
| 09 | 多课时引用同一道题 | 导入通过；ZIP 有重复条目警告 |
| 10 | 两个同名章节各含一个课时 | 失败，导入后课时数从 [1,1] 变为 [2,0] |
| 11 | 同一章节两个同名课时 | 失败，目录中的两个引用指向同一个课时 |
| 12 | 私有课程 is_public=0 | 失败，导入后变为 1 |
| 13 | 仅教师专属内容引用的编程题 | 失败，题目未打包 |
| 14 | ICPC 题的目标不存在场景 | 错误，要求独立题目包导入服务 |
| 15 | 非 ZIP 文件 | 通过，拒绝导入 |
| 16 | 缺少 course.json | 通过，拒绝导入 |
| 17–18 | Guest 导入、导出权限 | 通过，拒绝操作 |
| 19 | 多题同标题、引用较早的一题 | 失败，重绑到另一同名题 |
| 20 | program 块缺少 exercise ID | 错误，None.split 内部异常而非 ValidationError |
| 21 | 目标不存在场景中，同一课程包重复导入 | 失败，再次创建新题并改变关联 |
| 22 | 测验题目与分值跨目标往返 | 失败，原单题 5 分变为 1 分 |
| 23 | 作业跨目标往返 | 通过，题干保留 |
| 24 | 私有附件跨目标往返 | 失败，导入课时仍引用旧私有 URL，找不到对应 File |
| 25 | 缺失测验引用 | 通过，拒绝导入；与编程题不同 |
| 26 | 外部视频引用往返 | 通过，保留外部链接，不复制外部视频 |
| 27 | 无章节的空课程 | 通过 |

## 真实浏览器验收

使用本机 Chrome 完成管理员登录 → 上传 ZIP → 点击保存 → 自动跳转课程详情 → 打开设置页 → 导出菜单 → 下载 ZIP。确认中文课程说明、章节、课时显示正常，浏览器 pageerror 列表为空。对下载文件执行 ZIP CRC 检查，并校验标题、1 个章节、1 个课时以及解析后的中文正文，全部通过。

浏览器创建的临时课程删除接口返回 200，上传文件删除返回 202。最初的浏览器脚本因等待上传状态/设置标签定位不准确中断；修正为等待“移除文件”按钮出现及使用标准 `#settings` 地址后，最终流程完成。这些定位问题未计入业务缺陷。

浏览器日志见 `course-transfer-browser.log`。最后复查：本次审计前缀的课程、章节、课时、编程题、File 均为 0；浏览器测试课程与上传文件亦为 0。

## 已复现缺陷与代码位置

1. **私有课程转公开**：`lms/lms/course_import_export.py:get_course_fields`（约 465 行）未包含 `is_public`；新建课程使用默认 1。对已发布课程尤其需要优先修复。
2. **ICPC 不可移植**：导出仅走 `get_assessments_from_lesson`（86 行）的普通题路径；`build_assessment_doc`（677 行）直接插入触发 `lms_programming_exercise.py:27` 的包服务限制。
3. **同名章节错绑**：`get_chapter_name_for_lesson` / `add_lessons_to_chapters` 通过标题寻找章节，而非源 ID→新 ID 映射。
4. **同名课时错绑**：`add_lessons_to_chapters`（约 759 行）按课程和标题查询课时，无法区分同名课时。
5. **同名题错绑**：`replace_assessment_names`（594 行）按标题查题，无稳定源 ID 映射。
6. **重复迁移创建重复题**：`build_assessment_doc`（681 行）仅检查源内部 ID，首次迁移生成新 ID 后无法识别已导入对象。
7. **测验分值丢失**：`add_questions_to_quiz`（657 行）仅复制 question，不复制 marks，回落到默认 1。
8. **私有附件引用失效**：`create_asset_doc` 不恢复路径/私有属性，`replace_values_in_content`（612 行）未执行资产 URL 映射。实测旧 URL 对应 File 不存在，不能视为附件迁移成功。
9. **教师内容题目漏导出**：`get_assessments_from_lesson` 只遍历 `lesson.content`，不遍历 `instructor_content`。
10. **空题目块内部异常**：`get_assessment_title` 对空 ID 调用 split；应在解引用前验证并返回清晰错误。

此外，同一道题被多个课时引用会在 ZIP 中生成重复路径；目前用例能导入，但产生 zipfile Duplicate name 警告。

## 复跑

后端（特意保留失败，以便修复后回归）：

```sh
docker exec -u frappe -w /home/frappe/bench-data/frappe-bench \
  jwl-learning-frappe-1 env/bin/python \
  /workspace/lms/scripts/qa/course_transfer_audit.py
```

前端（本机已有隔离运行器）：

```sh
node /tmp/lms-editor-test-runtime/node_modules/vitest/vitest.mjs run \
  --config /tmp/lms-editor-test-runtime/course-transfer.config.mjs
```

原始日志：`course-transfer-backend.log`、`course-transfer-frontend.log`。测试脚本：`scripts/qa/course_transfer_audit.py`；前端新增测试：`frontend/src/tests/exportCourse.test.ts`。

范围限制：本次是功能和数据完整性审计，未进行大包压力、并发、ZIP 炸弹等安全专项；也未验证付款、证书及所有外部资源格式的跨站迁移。
