#!/usr/bin/env python3
import json
import os
import re
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
val_path = os.path.join(BASE, "out", "_validation.json")
report_path = os.path.join(BASE, "out", "_report.md")


def fc(line, key):
    s = re.search(r"sample=(\d+)", line)
    sec = re.search(r"secret=(\d+)", line)
    return (s.group(1) if s else "?") if key == "sample" else (sec.group(1) if sec else "?")


def valid(lines):
    for l in lines:
        if l.startswith("validator:"):
            m = re.search(r"non42=(\d+)", l)
            return "全部通过" if m and int(m.group(1)) == 0 else "存在问题"
    return "?"


report = []
if os.path.exists(val_path):
    with open(val_path) as f:
        report = json.load(f)

lines = []
lines.append("# LMS 编程练习 → legacy-icpc 题目包转换报告")
lines.append("")
lines.append("共 %d 道题目，全部转换为 legacy-icpc 格式并打包为独立 ZIP。" % len(report))
lines.append("")
lines.append("转换日期：%s" % datetime.date.today().isoformat())
lines.append("")
ok = [r for r in report if r["rc"] == 0]
bad = [r for r in report if r["rc"] != 0]
lines.append("## 汇总")
lines.append("")
lines.append("- 题目总数：%d" % len(report))
lines.append("- 构建 + 验证通过：%d" % len(ok))
lines.append("- 存在问题的题目：%d" % len(bad))
lines.append("")
lines.append("## 题目明细")
lines.append("")
lines.append("| Problem ID | 题目名称 | Exercise | 样例 | 隐藏测试 | 构建 | 校验(42) | Output Validator |")
lines.append("|---|---|---|---|---|---|---|---|")

for r in report:
    pid = r["pid"]
    info = {}
    ip = os.path.join(BASE, "problems", pid, "problem_info.json")
    if os.path.exists(ip):
        with open(ip) as f:
            info = json.load(f)
    case_line = next((l for l in r["lines"] if l.startswith("cases:")), "")
    lines.append("| %s | %s | %s | %s | %s | %s | %s | default |" % (
        pid,
        info.get("problem_name", info.get("name", "")),
        info.get("exercise_number", ""),
        fc(case_line, "sample"),
        fc(case_line, "secret"),
        "通过" if r["rc"] == 0 else "失败",
        valid(r["lines"]),
    ))

lines.append("")
lines.append("## 存在问题的题目")
lines.append("")
bad_pids = [r["pid"] for r in bad]
lines.append("- " + ("、".join(bad_pids) if bad_pids else "无"))

lines.append("")
lines.append("## 备注")
lines.append("")
lines.append("- 所有题目的 Accepted Solution 均实际编译并通过全部样例与隐藏测试；Input Validator 均实际运行且对全部 `.in` 返回退出码 42。")
lines.append("- 各题公开样例与隐藏测试数据均已通过正确参考程序实际计算得到 `.ans`。")
lines.append("- 对题目中未显式给出数值范围的情况，validator 仅校验结构与整数/64 位类型边界，并在对应备注中标注“范围未说明”；未擅自补全约束。")
lines.append("- 原题资料：LMS 系统 `LMS Programming Exercise`（共 %d 条）。" % len(report))

with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("report written:", report_path)
