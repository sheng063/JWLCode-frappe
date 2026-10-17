#!/usr/bin/env python3
import os, glob
BASE=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
PROBLEMS=os.path.join(BASE,"problems")
exts=(".yaml",".tex",".cpp",".py",".in",".ans",".json",".md",".txt")
def fix(path):
    with open(path,"rb") as f: data=f.read()
    if data.startswith(b"\xef\xbb\xbf"): data=data[3:]
    text=data.decode("utf-8", "replace")
    text=text.replace("\r\n","\n").replace("\r","\n")
    if text.strip() and not text.endswith("\n"):
        text=text+"\n"
    new=text.encode("utf-8")
    if new!=data:
        with open(path,"wb") as f: f.write(new)
        return True
    return False
changed=0
for pid in sorted(os.listdir(PROBLEMS)):
    prob=os.path.join(PROBLEMS,pid)
    if not os.path.isdir(prob): continue
    for root,dirs,files in os.walk(prob):
        dirs[:]=[d for d in dirs if d not in ("__pycache__","out")]
        for f in files:
            if f.endswith(exts):
                if fix(os.path.join(root,f)): changed+=1
print("normalized files:",changed)
