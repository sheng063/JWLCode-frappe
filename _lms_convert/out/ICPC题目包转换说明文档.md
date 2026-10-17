# ICPC 题目包（legacy-icpc）转换说明文档

> 本说明文档描述 LMS「编程练习」题目被转换为 **ICPC Problem Package `legacy-icpc`** 标准题包的过程、目录结构与文件语义、命名规则、生成与验证流程，并提供全量逐题对照表。

## 1. 概述

原始资料为学校 LMS 系统（`http://school.localhost:8000/lms/programming-exercises`）中的 **LMS Programming Exercise** 编程练习题目。全部题目均被转换为独立、自包含、可通过标准 OJ/评测系统导入的 ICPC 题目包（单题一个 ZIP），并逐题经过实际编译与运行验证。

- 题目总数：**83**
- 生成压缩包：**83 个** `<problemid>.zip`
- 公开样例数据组：**106**（63 题 1 组、19 题 2 组、1 题 5 组；全部取自原题题面并保持原样）
- 隐藏测试数据组：**808**（含原系统保留数据与按题面约束补充的边界/随机数据）
- 格式版本：`problem_format_version: legacy-icpc`
- 判定方式：全部为唯一答案题，`validation: default`（无需 Special Judge，故不生成 `output_validators/`）
- 参考解答：全部为 **C++17**（标准头文件、stdin→stdout），均已实际编译运行
- 构建 + 验证通过：**83 / 83**

## 2. 转换范围与来源

从 LMS 数据库 `LMS Programming Exercise`（共 83 条记录，编号 `P-000001`–`P-000083`）导出全部题目数据，包括：

- 题目名称与原始编号（exercise number）
- 题面 HTML（含 MathML 公式、代码片段、样例；3 题含图片，图片已一并下载进题包）
- 系统内保留的测试用例（输入 + 期望输出）
- 语言、时间/内存限制等元数据

其中 **1 题（`P-000083` 最大连续子段和）在系统中已是完整的 ICPC 包**，本次以原包为基础直接规范化导出（`maxsubarraysum.zip`，题面沿用 `problem.zh.pdf`）。其余 82 题由 HTML 题面重新组织为 legacy-icpc 标准题包。

## 3. 目标格式

严格采用 ICPC Problem Package **`legacy-icpc`** 格式（`problem_format_version: legacy-icpc`），未使用 `2025-09`、DOMjudge 私有格式、Hydro 私有格式或任何自定义格式。

## 4. 交付物

所有输出文件位于：**`/Users/jiang/Documents/LMS 题目`**

```text
/Users/jiang/Documents/LMS 题目/
├── <problemid>.zip      # 共 83 个独立题目包
├── ...
└── ICPC题目包转换说明文档.md   # 本文档
```

同一批题包（含生成脚本、验证记录与逐题中间数据）同时保留在工作目录：
`/Users/jiang/WorkSpace/JWLCode/JWLCode-frappe/_lms_convert/`

## 5. 单题包目录结构

每个 ZIP 内部包含唯一同名根目录 `<problemid>/`，结构如下：

```text
<problemid>.zip
└── <problemid>/
    ├── problem.yaml                         # 包元数据
    ├── problem_statement/
    │   └── problem.zh.tex                   # 中文题面（LaTeX，含 \problemname{题目名称}）
    │   （图片题另有 png/jpg 图片文件，随题面存放并引用）
    ├── data/
    │   ├── sample/                          # 公开样例（取自原题，保持原样）
    │   │   ├── 01.in
    │   │   └── 01.ans
    │   └── secret/                          # 隐藏测试数据
    │       ├── 01.in
    │       ├── 01.ans
    │       ├── ...
    │       └── NN.ans
    ├── submissions/
    │   └── accepted/
    │       └── solution.cpp                 # 参考解答（C++17）
    └── input_validators/
        └── validator.py                     # 输入校验器（成功 exit 42）
```

说明：本批题目均为唯一答案，无 Special Judge，因此不创建 `output_validators/` 目录。

## 6. 各文件规范说明

### 6.1 `problem.yaml`

```yaml
problem_format_version: legacy-icpc

name: 题目名称        # 使用原题题目名称（去除“C1 ·”等章节前缀）

license: unknown      # 未提供版权许可时固定为 unknown

validation: default   # 唯一答案，普通默认判定
```

- `author`：原始资料未提供作者，故不填写（未编造）。
- `source`：除沿用原 ICPC 包（P-000083）自带来源外，其余题源信息未在原始资料中明确给出，故不填写。

### 6.2 题面 `problem_statement/problem.zh.tex`

由原题 HTML/MathML 题面保真转换整理为：

```latex
\problemname{题目名称}

题目描述
输入格式
输出格式
约束条件（原题注明时列出）
样例输入 / 样例输出（verbatim 原样保留）
```

转换规则：

- 不改变题意：题目要求、输入/输出格式、数据范围、样例均按原文整理；仅修复明显排版问题。
- MathML 公式转为 LaTeX 数学式（如 `\le`、`\frac`、`p_{1}` 下标等）。
- 代码/常量以 `\texttt{...}` 呈现；样例块以 `verbatim` 原样呈现。
- 图片题（3 题）已将原站图片下载到 `problem_statement/` 并用 `\includegraphics` 引用。
- 剔除“本地评测说明”等非题目内容的提示文字。
- 原题包 P-000083 的题面沿用其自带的 `problem.zh.pdf`（legacy-icpc 允许 PDF 题面）。

### 6.3 公开样例 `data/sample/`

逐字保留原题公开样例的输入/输出，`XX.in` 与 `XX.ans` 同 basename 配对；原题有几个样例就放几组，未人为增减。

### 6.4 隐藏测试数据 `data/secret/`

- 包含原系统保留的非样例测试用例（`problem_info.json` 中 `secret_from_lms`，其 `.ans` 由原系统期望输出给出并逐一复核）。
- 另按各题约束补充覆盖边界（最小/最大）、极端与随机情况的 `.in` 用例。
- 所有 `.ans` 均由 **Accepted Solution 实际运行生成**（`.in` → 编译运行 → `.ans`），并全部通过原系统期望输出交叉校验。
- 编号统一为补零格式 `01.in`…（>99 组时为 `001.in`…），保证字典序与执行顺序一致。

### 6.5 参考解答 `submissions/accepted/solution.cpp`

- 每题为独立编写的 C++17 正确程序；只使用标准头文件（`<iostream>` 等，不依赖 `bits/stdc++.h` 之外的非标准头），从 stdin 读入、向 stdout 输出，无调试输出、不硬编码数据。
- 数值可能溢出 `int` 处使用 `long long`（如乘法、求和、绝对值等）。
- 所有参考解答均实际编译（`g++ -std=c++17 -O2`）并通过全部样例与隐藏测试。

### 6.6 输入校验器 `input_validators/validator.py`

每题按各自输入格式与约束单独编写（非复制通用模板），校验：

1. 输入结构（token 数量、行列结构）；
2. 数值类型与取值范围（仅以题面明确给出的范围为准）；
3. 必要的结构约束（如除法/取模不为零、递增序列等，题面有明确要求时）；
4. 输入结束后无多余非法数据。

退出码遵循 ICPC 规范：**校验成功 → `42`；失败 → 非 42（1）**。全部 `.in`（样例 + 隐藏）均已实测返回 42。

## 7. 题目命名规则（Problem ID）

- 目录名 / ZIP 文件名即 Problem ID，只含小写字母与数字：`^[a-z0-9]+$`。
- 无英文 ID 的题目按题目含义取简洁拼音/英文 slug（如 `A + B 问题` → `abwenti`、`最大连续子段和` → `maxsubarraysum`）。
- 原系统公开编号（`P-0000xx`）不作为文件名，但完整保留于本说明的第 8 节映射表及 `problem_info.json` 中，便于对照定位。

## 8. 全量逐题对照表

| 序号 | Problem ID（压缩包） | 题目名称 | 原题编号 | 样例 | 隐藏测试 | 备注 |
|---:|---|---|---|--:|--:|---|
| 1 | `abwenti` | A + B 问题 | P-000078 | 1 | 8 | — |
| 2 | `anyaoqiushuchu` | 按要求输出 | P-000032 | 2 | 1 | — |
| 3 | `banjiapiaowenti` | 半价票问题 | P-000056 | 1 | 13 | — |
| 4 | `baoguotuoyun` | 包裹托运 | P-000026 | 2 | 8 | — |
| 5 | `bianliangdeshengmingyushiyong` | 变量的声明与使用 | P-000068 | 1 | 8 | — |
| 6 | `boolleixing` | bool 类型 | P-000060 | 1 | 8 | — |
| 7 | `chengjipandingwenti` | 成绩判定问题 | P-000049 | 1 | 12 | — |
| 8 | `chengxugaicuo` | 程序改错 | P-000003 | 1 | 8 | 含图片题面 |
| 9 | `chengxushejit1` | 程序设计 T1 | P-000042 | 1 | 9 | — |
| 10 | `chengxushejit2` | 程序设计 T2 | P-000043 | 1 | 8 | — |
| 11 | `chengxushejit3` | 程序设计 T3 | P-000044 | 1 | 10 | — |
| 12 | `chufadezhengqueyunsuan` | 除法的正确运算 | P-000059 | 1 | 10 | — |
| 13 | `duozuchengfajisuan` | 多组乘法计算 | P-000079 | 1 | 7 | — |
| 14 | `eryueyouduoshaotian` | 二月有多少天 | P-000053 | 1 | 12 | — |
| 15 | `feipangwenti` | 肥胖问题 | P-000054 | 1 | 10 | — |
| 16 | `fenduandianfei` | 分段电费 | P-000036 | 2 | 8 | — |
| 17 | `fuzaqushuwei` | 复杂取数位 | P-000005 | 2 | 12 | — |
| 18 | `gudingchazhipanduan` | 固定差值判断 | P-000024 | 2 | 8 | — |
| 19 | `jianbeike` | 捡贝壳 | P-000066 | 1 | 10 | — |
| 20 | `jintianhuixiayuma` | 今天会下雨吗 | P-000022 | 1 | 9 | — |
| 21 | `jisuanguize` | 计算规则 | P-000027 | 2 | 8 | — |
| 22 | `jisuanjiandanchufa` | 计算简单除法 | P-000001 | 1 | 6 | — |
| 23 | `jisuanyunsuanjieguo` | 计算运算结果 | P-000081 | 1 | 8 | — |
| 24 | `jueduizhipaixu` | 绝对值排序 | P-000041 | 2 | 10 | — |
| 25 | `kacheyunshuhuowu` | 卡车运输货物 | P-000002 | 1 | 8 | — |
| 26 | `kaixuedianli` | 开学典礼 | P-000014 | 2 | 8 | — |
| 27 | `kaoshidengjihuafen` | 考试等级划分 | P-000055 | 1 | 12 | — |
| 28 | `keqianrenwudazilianxi` | 课前任务：打字练习 | P-000070 | 1 | 7 | — |
| 29 | `mainaitang` | 买奶糖 | P-000013 | 1 | 10 | — |
| 30 | `maxsubarraysum` | 最大连续子段和 | P-000083 | 5 | 18 | 题面为 PDF（沿用原题包）；原系统已为 ICPC 包，直接导出 |
| 31 | `nianlingdejisuan` | 年龄的计算 | P-000012 | 2 | 8 | — |
| 32 | `nihaoxiaomao` | 你好，小猫 | P-000082 | 1 | 8 | — |
| 33 | `p7deqibeishu` | 7 的奇倍数 | P-000028 | 2 | 10 | — |
| 34 | `pingguohechongzi` | 苹果和虫子 | P-000046 | 1 | 14 | — |
| 35 | `qiubutonggaodudedaqiyazhi` | 求不同高度的大气压值 | P-000017 | 1 | 10 | — |
| 36 | `qiuhe` | 求和 | P-000004 | 1 | 8 | — |
| 37 | `qiujueduizhi` | 求绝对值 | P-000020 | 2 | 10 | — |
| 38 | `qiumianjidewenti` | 求面积的问题 | P-000034 | 2 | 8 | — |
| 39 | `qushuwei` | 取数位 | P-000064 | 1 | 12 | — |
| 40 | `rili` | 日历 | P-000009 | 2 | 10 | 含图片题面 |
| 41 | `shifouweibeishuguanxi` | 是否为倍数关系 | P-000021 | 1 | 10 | — |
| 42 | `shixianjiaodegeshu` | 实现：角的个数 | P-000062 | 1 | 12 | — |
| 43 | `shixianwoniupashuwenti` | 实现蜗牛爬树问题 | P-000061 | 1 | 11 | — |
| 44 | `shiyishiluojiyunsuan` | 试一试逻辑运算 | P-000073 | 1 | 12 | — |
| 45 | `shuchubaoliu3weixiaoshudefudians` | 输出保留3位小数的浮点数 | P-000051 | 1 | 14 | — |
| 46 | `shuchuqiouxing` | 输出奇偶性 | P-000058 | 1 | 11 | — |
| 47 | `shujitu` | 数鸡兔 | P-000076 | 1 | 12 | — |
| 48 | `shuonihao` | 说你好 | P-000045 | 1 | 8 | 课程语言标记为 Python（参考解仍为 C++17） |
| 49 | `shuxuekaoshi` | 数学考试 | P-000018 | 1 | 8 | — |
| 50 | `shuzidetiqu` | 数字的提取 | P-000052 | 1 | 14 | — |
| 51 | `shuzipaixu` | 数字排序 | P-000048 | 1 | 13 | — |
| 52 | `siweishuzhongyououshuweima` | 四位数中有偶数位吗 | P-000035 | 2 | 8 | — |
| 53 | `sizeyunsuanxiaolian` | 四则运算小练 | P-000065 | 1 | 12 | — |
| 54 | `suantoujunchipingguo` | 蒜头君吃苹果 | P-000008 | 1 | 10 | — |
| 55 | `suantoujunchipingguo2` | 蒜头君吃苹果2 | P-000010 | 1 | 8 | — |
| 56 | `suantoujundangcaipan` | 蒜头君当裁判 | P-000037 | 2 | 10 | — |
| 57 | `suantoujundexinxika` | 蒜头君的信息卡 | P-000080 | 1 | 7 | — |
| 58 | `suantoujunmaiwenju` | 蒜头君买文具 | P-000011 | 1 | 8 | — |
| 59 | `suantoujunshangban` | 蒜头君上班 | P-000025 | 1 | 10 | — |
| 60 | `suantoujunxiangxiuxi` | 蒜头君想休息 | P-000019 | 2 | 8 | — |
| 61 | `suanyuanmenpiao` | 蒜园门票 | P-000031 | 1 | 9 | — |
| 62 | `tanchishechipingguo` | 贪吃蛇吃苹果 | P-000016 | 1 | 9 | — |
| 63 | `tianhuabanshangdexiaodeng` | 天花板上的小灯 | P-000006 | 1 | 8 | 含图片题面 |
| 64 | `tiaojianfenzhixiaojie` | 条件分支小结 | P-000071 | 1 | 12 | — |
| 65 | `tulingceshidejiandanmoni` | 图灵测试的简单模拟 | P-000074 | 1 | 6 | — |
| 66 | `wenduzhuanhuan` | 温度转换 | P-000030 | 1 | 8 | — |
| 67 | `wuzejisuanqi` | 五则计算器 | P-000072 | 1 | 15 | — |
| 68 | `xiaoshudechufa` | 小数的除法 | P-000007 | 1 | 10 | — |
| 69 | `xingqiwenti` | 星期问题 | P-000038 | 1 | 6 | — |
| 70 | `xingyundeshuzi` | 幸运的数字 | P-000039 | 2 | 10 | — |
| 71 | `xuanliwu` | 选礼物 | P-000023 | 1 | 8 | — |
| 72 | `yanyiyanguanxibiaodashi` | 验一验关系表达式 | P-000075 | 1 | 11 | — |
| 73 | `yigeyueyouduoshaotian` | 一个月有多少天 | P-000047 | 1 | 14 | — |
| 74 | `yigeyueyoujitian` | 一个月有几天 | P-000029 | 2 | 9 | — |
| 75 | `yongbianliangshixiangengduoyunsu` | 用变量实现更多运算 | P-000067 | 1 | 8 | — |
| 76 | `yongzhengxingbianliangcunchushis` | 用整型变量存储实数 | P-000077 | 1 | 12 | — |
| 77 | `youfei` | 邮费 | P-000040 | 1 | 10 | — |
| 78 | `yueshuhaishibeishu` | 约数还是倍数 | P-000057 | 1 | 12 | — |
| 79 | `zaisuanyunsuanjieguo` | 再算运算结果 | P-000069 | 1 | 8 | — |
| 80 | `zhangfangxingdemianji` | 长方形的面积 | P-000033 | 1 | 10 | — |
| 81 | `zhangfangxingdezhouzhang` | 长方形的周长 | P-000050 | 1 | 13 | — |
| 82 | `zhengchuyuqumodeyingyong` | 整除与取模的应用 | P-000015 | 2 | 10 | — |
| 83 | `zhengshusishewurudeshixian` | 正数四舍五入的实现 | P-000063 | 1 | 12 | — |

> 备注说明：**含图片题面**＝题面引用图片（已随包保存）；**题面为 PDF**＝沿用原 ICPC 包 PDF 题面；其余题面均为 `problem.zh.tex`。

## 9. 生成与验证流程

每题按以下标准流程生成并验证：

```text
① 从 LMS 导出原题（题面 HTML + 测试数据）
        │
        ▼
② 生成 problem.yaml 与 problem.zh.tex（HTML/MathML → LaTeX 保真转换）
        │
        ▼
③ 拆分公开样例 → data/sample（原样保留）
        │
        ▼
④ 编写参考解答 submissions/accepted/solution.cpp
        │
        ▼
⑤ 用原系统期望输出交叉校验参考解答（必须全部一致）
        │
        ▼
⑥ 编写 input_validators/validator.py（按本题格式/约束）
        │
        ▼
⑦ 补充隐藏测试 .in（边界/极端/随机，符合题面约束）
        │
        ▼
⑧ 编译并运行参考解答 → 生成/校验所有 .ans
        │
        ▼
⑨ 对全部 .in 运行输入校验器（必须 exit 42）
        │
        ▼
⑩ 打包 <problemid>.zip 并复检（结构、配对、编码、无杂项文件）
```

## 10. 验证结果汇总

- **参考解答编译**：83 / 83 通过（`g++ -std=c++17 -O2`）
- **公开样例测试**：全部一致（无 mismatch）
- **隐藏测试**：全部一致（`.ans` 由参考解答实际运行得到并复核）
- **输入校验器**：全部 `.in` 返回 42（无 non-42）
- **ZIP 结构检查**：全部通过（单一 `<problemid>/` 根、`.in/.ans` 配对、无 `__MACOSX`/`.DS_Store`/内部元数据文件、UTF-8 无 BOM、LF、非空文本以换行符结尾）
- 存在问题的题目：无

## 11. 编码与文本约定

- 所有文本文件：**UTF-8、无 BOM、Unix LF**；非空文本文件以换行符 `\n` 结尾（含全部 `.in` 输入文件，已逐一检查并修复）。
- 文件名不含中文/空格/分隔符，仅 `a-z 0-9` 与小写连排。

## 12. 题面保真与约束处理说明

- 全部题包以 LMS 原始题目为唯一题意依据；未修改题目要求、输入/输出格式、样例与数据范围。
- 对原题已明确给出的数值范围，validator 与测试数据严格按其取值（例如 `0<n<100`、`1≤a,b,c≤10000`、`n 为 10 的倍数`、`int 类型可存储范围` 等）。
- 对**原题未显式给出上限**的数值（如部分题目只写“整数”而未给范围），**未擅自补全具体范围**：validator 仅校验结构、整数性，以及参考解答实际需要的 64 位类型边界；此类情形如需严格数据范围，建议以题目出处/评测系统口径为准。
- 个别题目原始题面本身存在非常规字符或写法（例如“说你好”中的 `«`），按原文保留，未作改动。

## 13. 使用与导入建议

- 直接以 `problemid.zip` 导入支持 legacy-icpc 的 OJ / 评测平台（如 DOMjudge、自研 Judge Service 等）。
- 导入时评测语言可设为 C++（GNU C++17）；时间/内存限制以各平台与题库配置为准（系统内原值可在 `problem_info.json` 查看，LMS 运行限制记录于原系统 `judge_config`）。
- 若平台要求英文或其它语言题面，可在 `problem_statement/` 下按需新增 `problem.en.tex`，不影响包结构。

## 14. 汇总统计

- 题目总数：83
- 参考语言：C++17（全部）
- 公开样例组数合计：106
- 隐藏测试组数合计：808（其中 102 组来自原系统保留数据，其余为按约束补充）
- 含图片题面：3 题（`rili`、`chengxugaicuo`、`tianhuabanshangdexiaodeng`）
- PDF 题面：1 题（`maxsubarraysum`）
- 判定方式：`default`（无 Special Judge）
- 生成日期：2026-09-08

## 15. 附：转换工具与中间产物

转换工作目录：`/Users/jiang/WorkSpace/JWLCode/JWLCode-frappe/_lms_convert/`

```text
scripts/convert.py              # HTML + MathML → LaTeX 转换、样例抽取、ID 生成
scripts/gen_scaffold.py         # 生成题包骨架（yaml/题面/样例/系统数据拆分）
scripts/builder.py              # 单题构建：编译/交叉校验/生成.ans/校验器42/打包
scripts/validate_all.py         # 全量复验脚本
scripts/rezip_all.py            # 重新打包
scripts/generate_report.py      # 生成转换报告 _report.md
problems/<problemid>/           # 每题构建中间目录（含 problem_info.json）
out/                            # 生成的 <problemid>.zip、验证与报告文件
work/                           # 从 LMS 导出的原始数据（exercises/test_cases/...json）
```

---
（文档内容与题目包数据一一对应，随题目包同步维护。）

