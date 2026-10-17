#!/usr/bin/env python3
"""Build legacy-icpc package scaffolds for all manual LMS exercises.

For each exercise we generate:
  <work>/problems/<pid>/problem.yaml
  <work>/problems/<pid>/problem_statement/problem.zh.tex   (+ downloaded images)
  <work>/problems/<pid>/data/sample/<NN>.in / <NN>.ans     (public samples)
  <work>/problems/<pid>/data/secret/<NN>.in / <NN>.ans     (LMS non-sample cases)
  <work>/problems/<pid>/problem_info.json                  (metadata for the builder)

The accepted solution, input validator and any additional secret data are added
later, then everything is validated and zipped.
"""
import json
import os
import re
import urllib.parse
import urllib.request

import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from convert import (  # noqa: E402
    extract_samples,
    render_statement_latex,
    slug_for_id_unique,
)

WORK = os.path.join(HERE, "..")
PROBLEMS = os.path.join(WORK, "problems")
BASE_STATEMENT_URL = "http://school.localhost:8000"

ICPCS = {"P-000083"}  # exercises that already have an ICPC package (handled separately)


def read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def clean_name(title):
    n = re.sub(r"^C\d+\s*[·.:\-~]\s*", "", title or "").strip()
    n = re.sub(r"\s*\[[0-9]+\]\s*$", "", n).strip()
    return n


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


def build_scaffold(ex):
    name_id = ex["name"]
    num = ex["exercise_number"]
    title = ex["title"]
    pid = slug_for_id_unique(title, USED)
    pdir = os.path.join(PROBLEMS, pid)
    os.makedirs(pdir, exist_ok=True)

    statement_html = ex["problem_statement"] or ""
    img_dir = os.path.join(pdir, "problem_statement")
    os.makedirs(img_dir, exist_ok=True)

    # Download referenced images (rewrite src to local filename in the output)
    img_map = {}
    for src in re.findall(r'<img\b[^>]*src=["\']([^"\']+)["\'][^>]*>', statement_html, re.I):
        fname = os.path.basename(urllib.parse.urlparse(src).path)
        if not fname:
            continue
        url = src if src.startswith("http") else BASE_STATEMENT_URL + src
        local = os.path.join(img_dir, fname)
        if fetch_image(url, local):
            img_map[src] = fname

    # Render statement LaTeX with image dir so \includegraphics uses local names
    body = render_statement_latex(statement_html, image_dir=img_dir)
    # The renderer uses basename of src; ensure consistent by rewriting image refs
    # to the actual saved filename.
    for src, fname in img_map.items():
        body = body.replace("{%s}" % os.path.basename(urllib.parse.urlparse(src).path), "{%s}" % fname)

    tex = STATEMENT_TEMPLATE.replace("@@NAME@@", _latex_escape(clean_name(title))).replace("@@BODY@@", body)
    write_text(os.path.join(pdir, "problem_statement", "problem.zh.tex"), tex)

    # problem.yaml
    yaml_lines = []
    yaml_lines.append("problem_format_version: legacy-icpc")
    yaml_lines.append("")
    yaml_lines.append("name: " + clean_name(title))
    yaml_lines.append("")
    yaml_lines.append("license: unknown")
    yaml_lines.append("")
    yaml_lines.append("validation: default")
    yaml_lines.append("")
    write_text(os.path.join(pdir, "problem.yaml"), "\n".join(yaml_lines) + "\n")

    # public samples from statement
    samples = extract_samples(statement_html)
    # LMS test cases for this exercise
    lms_tc = [t for t in TESTCASES if t["parent"] == name_id]
    lms_tc.sort(key=lambda t: (t.get("idx") or 0))

    sample_dir = os.path.join(pdir, "data", "sample")
    secret_dir = os.path.join(pdir, "data", "secret")
    os.makedirs(sample_dir, exist_ok=True)
    os.makedirs(secret_dir, exist_ok=True)

    sample_inputs = [s[0] for s in samples]

    # Write public samples
    for i, (sin, sout) in enumerate(samples, 1):
        write_text(os.path.join(sample_dir, "%02d.in" % i), sin + ("\n" if sin and not sin.endswith("\n") else ""))
        write_text(os.path.join(sample_dir, "%02d.ans" % i), sout + ("\n" if sout and not sout.endswith("\n") else ""))

    # LMS cases not equal to a public sample -> secret, using LMS ground truth
    secret_cases = []
    for t in lms_tc:
        if t["input"] in sample_inputs:
            continue
        secret_cases.append({"idx": t.get("idx"), "input": t["input"], "output": t["expected_output"]})
    for i, c in enumerate(secret_cases, 1):
        write_text(os.path.join(secret_dir, "%02d.in" % i), c["input"] + ("\n" if c["input"] and not c["input"].endswith("\n") else ""))
        write_text(os.path.join(secret_dir, "%02d.ans" % i), c["output"] + ("\n" if c["output"] and not c["output"].endswith("\n") else ""))

    # problem_info.json (all metadata the builder needs)
    info = {
        "exercise_name": name_id,
        "exercise_number": num,
        "title": title,
        "problem_id": pid,
        "problem_name": clean_name(title),
        "language": ex.get("language", "C++"),
        "time_limit_seconds": ex.get("time_limit_seconds"),
        "memory_limit_kb": ex.get("memory_limit_kb"),
        "evaluation_mode": ex.get("evaluation_mode"),
        "source_type": ex.get("source_type"),
        "samples": [{"input": s[0], "output": s[1]} for s in samples],
        "lms_test_cases": [{"idx": t.get("idx"), "input": t["input"], "output": t["expected_output"]} for t in lms_tc],
        "secret_from_lms": secret_cases,
        "statement_html_len": len(statement_html),
        "images": list(img_map.values()),
        "base_statement_url": BASE_STATEMENT_URL,
    }
    with open(os.path.join(pdir, "problem_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print("BUILT %-8s %-32s pid=%-32s samples=%d secret_lms=%d" % (num, title[:34], pid, len(samples), len(secret_cases)))
    return pid


def _latex_escape(s):
    # Escape LaTeX specials but keep CJK intact (handled by ctex).
    out = []
    for c in s or "":
        if c in "\\{}_$%&#~^":
            out.append("\\" + c)
        else:
            out.append(c)
    return "".join(out)


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
    WORK_DIR = os.path.abspath(os.path.join(HERE, ".."))
    PROBLEMS = os.path.join(WORK_DIR, "problems")
    os.makedirs(PROBLEMS, exist_ok=True)
    WORK = WORK_DIR

    EXERCISES = read_json(os.path.join(WORK_DIR, "work", "exercises.json"))
    TESTCASES = read_json(os.path.join(WORK_DIR, "work", "test_cases.json"))
    USED = set()
    for ex in EXERCISES:
        if ex["exercise_number"] in ICPCS:
            print("SKIP icpc already packaged:", ex["exercise_number"], ex["title"])
            continue
        build_scaffold(ex)
    print("TOTAL built:", len(os.listdir(PROBLEMS)))
