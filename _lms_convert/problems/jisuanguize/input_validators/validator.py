#!/usr/bin/env python3
"""Validate input for problem 'jisuanguize' (计算规则).

Input format (from problem_statement/problem.zh.tex):
  A single integer x, with 0 <= x < 100.
Output format:
  Output the value computed by the piecewise rules.

The validator checks the input matches exactly the stated format and the
stated constraint (exactly one base-10 integer token with 0 <= x < 100).
On valid input it exits with code 42; on invalid input it prints a short
message to stderr and exits with code 1.
"""
import re
import sys

MIN_X = 0
MAX_X = 99


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

    x = int(tok)
    if not (MIN_X <= x <= MAX_X):
        sys.stderr.write("x out of range: %d\n" % x)
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
