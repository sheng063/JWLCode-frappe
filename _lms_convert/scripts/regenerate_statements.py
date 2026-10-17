#!/usr/bin/env python3
"""Regenerate only problem_statement/problem.zh.tex (+ images) for all problems.

Does NOT touch data/, submissions/, input_validators/, problem.yaml, or
problem_info.json. Skips packages that use a PDF statement (e.g. maxsubarraysum).
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from convert import render_statement_latex  # noqa: E402

BASE = os.path.join(HERE, "..")
PROBLEMS = os.path.join(BASE, "problems")
SRC_URL = "http://school.localhost:8000"


def read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _latex_escape(s):
    out = []
    for c in s or "":
        out.append("\\" + c if c in "\\{}_$%&#~^" else c)
    return "".join(out)


def fetch_image(url, local_path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(local_path, "wb") as f:
            f.write(data)
        return True
    except Exception as exc:
        print("  IMAGE FAIL", url, exc)
        return False


TEMPLATE = open(os.path.join(HERE, "_statement_template.txt"), encoding="utf-8").read() if os.path.exists(
    os.path.join(HERE, "_statement_template.txt")
) else None


def main():
    # exercises keyed by primary key (exercise_name)
    exercises = {e["name"]: e for e in read_json(os.path.join(BASE, "work", "exercises.json"))}
    count = 0
    for pid in sorted(os.listdir(PROBLEMS)):
        pdir = os.path.join(PROBLEMS, pid)
        ip = os.path.join(pdir, "problem_info.json")
        if not os.path.isdir(pdir) or not os.path.exists(ip):
            continue
        info = read_json(ip)
        ename = info.get("exercise_name")
        if not ename or ename not in exercises:
            continue
        e = exercises[ename]
        stmt_html = e.get("problem_statement") or ""
        if not stmt_html or "<p>" not in stmt_html:
            continue  # e.g. PDF-linked package
        # clean_name (same as scaffold)
        name = info.get("problem_name") or info["title"]
        img_dir = os.path.join(pdir, "problem_statement")
        os.makedirs(img_dir, exist_ok=True)
        img_map = {}
        for src in re.findall(r'<img\b[^>]*src=["\']([^"\']+)["\'][^>]*>', stmt_html, re.I):
            fname = os.path.basename(urllib.parse.urlparse(src).path)
            if not fname:
                continue
            url = src if src.startswith("http") else SRC_URL + src
            local = os.path.join(img_dir, fname)
            if fetch_image(url, local):
                img_map[src] = fname
        body = render_statement_latex(stmt_html, image_dir=img_dir)
        for src, fname in img_map.items():
            body = body.replace("{%s}" % os.path.basename(urllib.parse.urlparse(src).path), "{%s}" % fname)

        tex = (TEMPLATE or STATEMENT_TEMPLATE).replace("@@NAME@@", _latex_escape(name)).replace("@@BODY@@", body)
        write_text(os.path.join(pdir, "problem_statement", "problem.zh.tex"), tex)
        count += 1
    print("regenerated statements:", count)


STATEMENT_TEMPLATE = """\\documentclass{article}
\\usepackage[UTF8]{ctex}
\\usepackage{amsmath}
\\usepackage{amssymb}
\\usepackage{graphicx}
\\usepackage{geometry}
\\geometry{a4paper, margin=2cm}

\\newcommand{\\problemname}[1]{\\begin{center}\\Large\\bfseries #1\\end{center}}
\\usepackage{enumitem}

\\begin{document}
\\problemname{@@NAME@@}

@@BODY@@
\\end{document}
"""


if __name__ == "__main__":
    main()
