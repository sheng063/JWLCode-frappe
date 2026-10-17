# ICPC 题目包完整格式说明与生成后检查要点

> 适用范围：ICPC Problem Package **`legacy-icpc`** 单题压缩包（`problem_format_version: legacy-icpc`）。
> 本文分为两部分：**第一部分**给出 `legacy-icpc` 完整格式规范；**第二部分**给出题目包生成完成后应当执行的检查内容与注意事项。

---

# 第一部分 `legacy-icpc` 完整格式说明

## 1. 包与目录

每个题目是**一个独立 ZIP**，ZIP 内部必须只有一个同名根目录，禁止多级外层目录。

```text
problemid.zip
└── problemid/                        # 根目录名 = ZIP 文件名 = Problem ID
    ├── problem.yaml                  # 必需：包元数据
    ├── problem_statement/
    │   └── problem.zh.tex            # 必需：中文题面（也可为 problem.en.tex / *.pdf）
    ├── data/
    │   ├── sample/                   # 可选：公开样例
    │   │   ├── 01.in
    │   │   └── 01.ans
    │   └── secret/                   # 必需：隐藏测试数据（至少 1 组）
    │       ├── 01.in
    │       ├── 01.ans
    │       └── ...
    ├── submissions/
    │   └── accepted/
    │       └── solution.cpp          # 必需：参考解答
    └── input_validators/
        └── validator.py              # 必需：输入校验器
```

需要特殊判题时再增加：

```text
    └── output_validators/
        └── validator.cpp             # 仅 validation: custom 时存在
```

- **禁止**出现 `__MACOSX/`、`.DS_Store`、`Thumbs.db`、编辑器备份、临时文件等无关文件。
- **禁止**在包内保留内部元数据文件（如构建期的 `problem_info.json`、编译产物 `*.exe`、`*.pyc` 等）。

## 2. 命名规则

| 对象 | 规则 | 示例 |
|---|---|---|
| Problem ID / 根目录 / ZIP 文件名 | 仅小写字母与数字 `^[a-z0-9]+$`，不用中文、连字符、下划线 | `abwenti`、`maxsubarraysum`、`problem001` |
| 测试文件 | 统一补零编号，按 basename 字典序处理：`01.in/01.ans`…；超过 99 组用 `001.in` | 禁止 `1.in`、`10.in` 混排 |
| 公开样例 | `01.in` 与 `01.ans` 同 basename 配对 | 禁止 `01.in` + `answer01.ans` |
| 语言代码 | 中文题面 `zh`、英文 `en` | `problem.zh.tex` |

## 3. `problem.yaml`

```yaml
problem_format_version: legacy-icpc    # 固定，不得使用 2025-09 等其它值
name: 题目名称                          # 原始题目名称
license: unknown                       # 未明确授权时固定 unknown
validation: default                    # default | custom
```

- `author`：仅原始资料明确提供作者时填写，不得编造。
- `source`：仅原始资料明确提供赛事/题库/课程来源时填写。
- `license`：用户未提供版权许可时一律 `unknown`，不得自行填 `educational` 等。
- `validation: default`：答案唯一（整数/字符串/数组/唯一确定答案）时使用普通 diff 判定。
- `validation: custom`：仅当输出不唯一或需特殊判定时使用，此时**必须**提供 `output_validators/`。
  - 不要因“不确定”而使用 `custom`；也不要对普通题凭空加 Special Judge。
- 可选字段（如 `limits`、`keywords`、`source` 等）以原题包为准，不影响规范性。

## 4. 题面 `problem_statement/`

- 优先提供 LaTeX：`problem.zh.tex`；确实无法可靠转 LaTeX 时才提供 `problem.zh.pdf`。
- 题面必须以 `\problemname{题目名称}` 开头，按“题目描述 / 输入格式 / 输出格式 / 约束条件 / 样例”组织。
- 只描述题目本身；输入输出样例块以 `verbatim` 或代码块原样保留。
- 图片放入 `problem_statement/` 并用 `\includegraphics` 引用，禁止引用外部网络路径。
- 只允许整理排版，**不得改变题意、样例与数据范围**。

## 5. 数据目录 `data/`

### 5.1 `data/sample/`（可选）

- 与原题公开样例一一对应：原题几组就放几组，不人为增减、不替换。
- `.in` 与 `.ans` 必须同名配对，内容保持原样。

### 5.2 `data/secret/`（必需）

- 至少 1 组合法用例；实际教学中建议按题目复杂度生成 10–20 组覆盖：
  最小边界、最大边界、普通随机、特殊结构、极端情况、易错情况、溢出风险、复杂度极限等。
- 只生成**符合题面约束**的数据，不得违反约束（允许重边则不得禁止重边等）。
- 每组 `.ans` 必须由**正确参考程序实际运行**得到；禁止肉眼/AI 猜测批量答案。

## 6. 参考解答 `submissions/accepted/solution.cpp`

- 默认 C++17（除非题目明显需要其它语言）。
- 从 stdin 读入、向 stdout 输出；无调试输出；不硬编码测试数据；不使用非标准输入文件。
- 使用足够大的整数类型（可能溢出 `int` 时用 `long long`）；避免未定义行为。
- 文件名统一 `solution.cpp`，不以算法名强制命名（参考解是“正确解答”，不要求特定算法）。

## 7. 输入校验器 `input_validators/validator.py`

- 每个题目**按本题目输入格式/范围/结构单独编写**，禁止全题共用同一模板。
- Python 3 校验器，文件头带 shebang：`#!/usr/bin/env python3`。
- 必须检查：输入结构、数字数量、数值范围（只以题面明确给出的为准）、必要结构约束、结束后无多余数据。
- **退出码是 ICPC 约定，非常重要**：

```text
校验成功 → exit 42
校验失败 → 非 42（通常 1），并向 stderr 输出原因
```

不能使用普通程序习惯的“成功 → exit 0”。

## 8. 输出校验器 `output_validators/`（仅 custom）

- Accepted → `exit 42`；Wrong Answer → `exit 43`；其它退出码表示校验器自身异常。

## 9. 特殊题型

| 题型 | 处理 |
|---|---|
| 浮点误差题 | 误差要求以原题为准设置 validator；不得自行定为 `1e-6`/`1e-9` |
| 多解题（多种合法输出） | `validation: custom` + 真实 Output Validator，不能只放一份 `.ans` 用 diff |
| 交互题 | 不得按普通题处理，须按 legacy-icpc 交互规范制作并明确标记 |
| 无输入题 | 允许 `.in` 为空；仍应生成对应测试文件与固定输出 `.ans` |

## 10. 文本编码与打包

- 所有文本：**UTF-8、无 BOM、Unix LF**；非空文本文件以换行符 `\n` 结尾（**含 `.in` 输入文件**）。
- ZIP 用 zip 打包，单一根目录；不带外层多余目录、系统垃圾文件。

---

# 第二部分 生成后的检查内容与注意事项

生成题包后，**只创建文件不算完成**，必须按下述清单逐项实际执行检查，全部通过才可交付。

## A. 结构检查（目录级）

- [ ] `problem.yaml` 存在且可被 YAML 解析。
- [ ] `problem_statement/` 存在（含 `problem.zh.tex` 或 `.pdf`）。
- [ ] `data/secret/` 存在且至少 1 组 `.in/.ans`。
- [ ] `submissions/accepted/` 存在（含 `solution.cpp`）。
- [ ] `input_validators/` 存在（含 `validator.py`）。
- [ ] `data/sample/` 存在（若有公开样例）。
- [ ] 若 `problem.yaml` 为 `validation: custom` → 存在 `output_validators/`；若为 `default` → **不要**创建该目录。

## B. `problem.yaml` 检查

- [ ] `problem_format_version: legacy-icpc`（确认为该值，而非 `2025-09` 或私有格式）。
- [ ] `name` 为原始题目名称；`license: unknown`（未授权时）。
- [ ] `validation` 取值与题面/答案性质一致（唯一答案 → default）。

## C. 题面检查

- [ ] 以 `\problemname{题目名称}` 开头，含“描述 / 输入格式 / 输出格式 / 约束 / 样例”结构。
- [ ] 题面内容与原始题意一致（未擅自改范围/样例/规则）。
- [ ] 样例块数据与 `data/sample/*` 一致。
- [ ] 图片文件确实存在且被引用（无 404 外部链接）；LaTeX 内无残留占位符/控制字符/未替换标记。
- [ ] 编码 UTF-8 无 BOM、LF；文件以换行结尾。

## D. 数据检查

- [ ] `.in` 与 `.ans` 逐组配对：不存在有 `.in` 无 `.ans`、或有孤立 `.ans`。
- [ ] 编号补零、字典序正确（`01…`，超过 99 用 `001…`）。
- [ ] 所有 `.in` 内容符合题面输入格式与约束（可由 Input Validator 复核）。
- [ ] 所有 `.ans` 为正确参考程序运行结果，并通过原系统/已知期望输出交叉验证。
- [ ] 非空 `.in`/`.ans`/文本文件均以换行符结尾；无 CRLF、无 BOM。
- [ ] 无意外重复或违反约束的测试数据。

## E. 参考解答检查

- [ ] `g++ -std=c++17 -O2`（或对应编译器）**实际编译成功**。
- [ ] 对 `data/sample/*.in` 与 `data/secret/*.in` **逐组运行**，输出与 `*.ans` 完全一致。
- [ ] 无调试输出、无硬编码数据、不读写非标准文件。
- [ ] 数值类型足够（溢出安全）；未使用非标准头依赖。

## F. 输入校验器检查

- [ ] 对每个 `data/sample/*.in` 与 `data/secret/*.in` 运行 `validator.py`，**退出码均为 42**。
- [ ] 用若干**非法输入**（数量错、越界、类型错、多余 token、结构违规）实测，退出码非 42。
- [ ] 校验内容与本题输入格式/范围匹配（非通用模板）；范围只取题面明确给出的。

## G. ZIP 打包检查

- [ ] ZIP 可正常解压、无损坏（`unzip -t`）。
- [ ] 内部仅一个同名根目录 `problemid/`，无外层多余目录。
- [ ] 无 `__MACOSX/`、`.DS_Store`、`Thumbs.db`、内部元数据（`problem_info.json`）、编译产物（`*.exe`、`*.pyc`）。
- [ ] 文件路径与 §1 结构一致；basename 与根目录同名。

## H. 常见“注意”清单（易错点）

1. **退出码**：Input Validator 成功是 **42**，不是 0；失败非 42。Output Validator 是 42 / 43。
2. **范围不猜测**：题面未给出的数值上限不要自行补全（validator 只按明确范围 + 类型边界校验，并注明“范围未说明”）。
3. **样例不改动**：公开样例即使“不够好”也不替换、不增删。
4. **`.ans` 不手写**：必须由参考程序实际运行生成；参考解需先用已知期望输出交叉验证正确性。
5. **校验器逐题定制**：图/树/数组/范围各不相同，禁止全题复制同一份。
6. **普通题不加 Special Judge**：只有输出不唯一/需浮点容差等才 `custom`。
7. **文本编码**：无 BOM、LF 换行、末尾换行（含空白类 `.in`）。
8. **无输入题**：允许 `.in` 为空；校验器应接受空输入（exit 42），参考解输出固定内容。
9. **图片题**：图片须随包保存并在题面中引用本地文件，不留外部链接。
10. **交接前复验**：修改过任何文件（如补末尾换行、改题面、重打包）后，应重新执行 D–G 全部检查，再刷新交付目录。

## I. 建议的自动化验证（等价于手工清单）

对每个题目目录依次执行（可在 CI 或脚本中落地）：

```bash
# 1) 编译参考解答
g++ -std=c++17 -O2 -o /tmp/sol submissions/accepted/solution.cpp

# 2) 逐组运行并 diff（.ans 缺失时由运行结果生成）
for f in data/sample/*.in data/secret/*.in; do
  /tmp/sol < "$f" > "$f.out"
  diff -q "${f%.in}.ans" "$f.out" || echo "MISMATCH: $f"
done

# 3) 输入校验器必须返回 42
for f in data/sample/*.in data/secret/*.in; do
  python3 input_validators/validator.py < "$f" || echo "VALIDATOR: $f rc=$?"
done
# 实际以脚本记录退出码并断言 == 42

# 4) 结构 / 配对 / 编码 / ZIP 完整性检查（见 D、F、G）
```

> 说明：以上自动化步骤与本批次实际使用的 `_lms_convert/scripts/builder.py`、`validate_all.py` 检查逻辑一致（编译、LMS 期望输出交叉校验、生成/核对 `.ans`、validator 42、打包、结构与编码复检）。

---

*文档版本：1.0（随 83 题 `legacy-icpc` 题包批次维护）*
