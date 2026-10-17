#!/usr/bin/env python3
"""Compile each spec's C++ reference solution and verify test cases.

Implements judge0-style output comparison: trailing whitespace on each line
and trailing newlines are ignored, yielding a normalized string.
Prints a per-spec report and returns non-zero exit if any check fails.
"""
import json
import os
import subprocess
import sys
import tempfile

SPEC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs")


def norm(s: str) -> str:
    lines = s.splitlines()
    lines = [l.rstrip() for l in lines]
    return "\n".join(lines).rstrip("\n")


def run_case(cpp: str, stdin_text: str, timeout=5):
    """Compile the C++ solution once and run it on the given stdin. Returns (ok, stdout, err)."""
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "main.cpp")
        exe = os.path.join(td, "main")
        with open(src, "w", encoding="utf-8") as f:
            f.write(cpp)
        comp = subprocess.run(
            ["g++", "-std=c++17", "-O2", "-x", "c++", "-o", exe, src],
            capture_output=True, text=True, timeout=timeout,
        )
        if comp.returncode != 0:
            return False, None, comp.stderr
        run = subprocess.run(
            [exe], input=stdin_text, capture_output=True, text=True, timeout=timeout,
        )
        return True, run.stdout, ""


def main():
    specs = sorted(f for f in os.listdir(SPEC_DIR) if f.endswith(".json"))
    if not specs:
        print("No specs found in", SPEC_DIR)
        return 0
    failures = 0
    for fname in specs:
        path = os.path.join(SPEC_DIR, fname)
        spec = json.load(open(path, encoding="utf-8"))
        cpp = spec.get("cpp_solution", "")
        title = spec.get("title", fname)
        # compile once per spec
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "main.cpp")
            exe = os.path.join(td, "main")
            with open(src, "w", encoding="utf-8") as f:
                f.write(cpp)
            comp = subprocess.run(
                ["g++", "-std=c++17", "-O2", "-x", "c++", "-o", exe, src],
                capture_output=True, text=True, timeout=10,
            )
            if comp.returncode != 0:
                print(f"[COMPILE ERROR] {spec.get('assignment')} ({title}):\n{comp.stderr[-1500:]}")
                failures += 1
                continue
            for tc in spec.get("test_cases", []):
                inp = tc.get("input", "")
                exp = tc.get("expected_output", "")
                run = subprocess.run([exe], input=inp, capture_output=True, text=True, timeout=10)
                got = norm(run.stdout)
                expn = norm(exp)
                status = "OK" if got == expn else "MISMATCH"
                if status == "MISMATCH":
                    failures += 1
                    print(f"[MISMATCH] {spec.get('assignment')} ({title}) input={inp!r}")
                    print(f"    expected={exp!r}")
                    print(f"    got     ={run.stdout!r}")
    print(f"\n=== {len(specs)} specs, {failures} failures ===")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
