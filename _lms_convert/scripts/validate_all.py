#!/usr/bin/env python3
import os, subprocess, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
PY = os.path.join(BASE, "venv", "bin", "python")
builder = os.path.join(HERE, "builder.py")
problems = sorted(os.listdir(os.path.join(BASE, "problems")))
report = []
for pid in problems:
    d = os.path.join(BASE, "problems", pid)
    if not os.path.isdir(d):
        continue
    r = subprocess.run([PY, builder, d], capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    wanted = [l for l in tail if l.startswith(("compiled","cross_check","cases:","validator:","zip ->","FAIL"))]
    report.append({"pid": pid, "rc": r.returncode, "lines": wanted})
    print(("%s rc=%d" % (pid, r.returncode)), flush=True)
ok = [x for x in report if x["rc"]==0]
bad = [x for x in report if x["rc"]!=0]
print("\n=== TOTAL %d OK %d FAIL %d ===" % (len(report), len(ok), len(bad)))
for x in bad:
    print("FAIL", x["pid"])
    for l in x["lines"]: print("   ", l)
import json
with open(os.path.join(BASE, "out", "_validation.json"), "w") as f:
    json.dump(report, f, indent=2)
