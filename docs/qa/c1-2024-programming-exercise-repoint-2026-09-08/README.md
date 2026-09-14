# c1-2024 编程课时练习引用修复记录（2026-09-08）

目标站点：http://school.localhost:8000（site `school.localhost`），课程 `c1-2024`（C++/C1 课程）。

## 问题

课程 c1-2024 共 215 个课时，其中 **81 个编程课时**（content 中带 `program` 块）引用的
`LMS Programming Exercise` 记录已不存在（悬空引用，全部失效）。系统题库中已有同源的
83 道 ICPC 编程题（P-000085 起），其中 81 道与本课程课时对应。

## 处理

对 81 个课时逐一将其 `content.blocks[].program.data.exercise` 由失效记录改写为题库中
**同名题目**的实际记录：

- 78 个课时按课时标题与题库题目标题完全同名匹配；
- 3 个课时标题为题目变体写法，经用户确认按同一道题对应：
  - `你好小猫` → `你好，小猫`（P-000116）
  - `让我们一起说你好` → `说你好`（P-000132）
  - `用整型变量存储实数会怎么样呢` → `用整型变量存储实数`（P-000160）

保存走正常 `Course Lesson` 校验，课时类型（lesson_type）统一归一为 `Programming`
（此前 37 个为空）。修改前已备份全部受影响课时原始 `content`。

## 结果（修改后核验）

- 81/81 个编程课时引用均指向存在的题目，0 悬空；
- 被引用题目全部为 `source_type = icpc`；
- 课程课时类型分布：Programming 81、Text 46、其余 88 个无内容标记（Text 类内容课时）。

## 文件

- `backup_c1_2024_lessons.json` — 修改前受影响课时完整快照（name/title/chapter/lesson_type/content/modified）
- `mapping_course.json` — 81 个课时的 旧引用→新引用 映射清单（含 exact/fuzzy 标记）
- `fix_report_c1_2024.json` — 执行报告（逐课时 old→new、修改后 lesson_type）

回滚：按 `backup_c1_2024_lessons.json` 恢复各课时 `content`（及 `lesson_type`）即可。
