#!/usr/bin/env python3
"""Validate input for problem 'qiuhe' (求和).

Input format (from problem_statement/problem.zh.tex):
  A single integer n (1 <= n <= 1000000).
Output format:
  The single integer equal to 1+2+3+...+n.

This validator checks the input matches exactly the stated format and
constraint. On valid input it exits with code 42; on invalid input it prints
a short message to stderr and exits with code 1.
"""
import re
import sys

MIN_N = 1
MAX_N = 1000000


def main():
    data = sys.stdin.read()
    s = data.strip()
    if not s:
        sys.stderr.write("empty input\n")
        return 1

    tokens = s.split()
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer\n")
        return 1

    tok = tokens[0]
    if not re.fullmatch(r"[0-9]+", tok):
        sys.stderr.write("not a base-10 integer: %s\n" % tok)
        return 1

    n = int(tok)
    if not (MIN_N <= n <= MAX_N):
        sys.stderr.write("n out of range: %d\n" % n)
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
