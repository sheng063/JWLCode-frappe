#!/usr/bin/env python3
import os, zipfile, glob
HERE=os.path.dirname(os.path.abspath(__file__))
BASE=os.path.join(HERE,"..")
PROBLEMS=os.path.join(BASE,"problems")
OUT=os.path.join(BASE,"out")
os.makedirs(OUT, exist_ok=True)
count=0
for pid in sorted(os.listdir(PROBLEMS)):
    prob=os.path.join(PROBLEMS,pid)
    if not os.path.isdir(prob): continue
    zpath=os.path.join(OUT,pid+".zip")
    with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as z:
        for root,dirs,files in os.walk(prob):
            dirs[:]=[d for d in dirs if d not in ("__pycache__","out")]
            for f in files:
                if f in ("solution.exe","problem_info.json") or f.endswith(".pyc"): continue
                full=os.path.join(root,f)
                rel=os.path.relpath(full,prob)
                z.write(full,pid+"/"+rel)
    count+=1
print("rezipped:",count)
