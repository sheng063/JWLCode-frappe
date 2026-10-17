#!/usr/bin/env python3
"""Input validator for the 二月有多少天 problem.

Input format (from problem_statement/problem.zh.tex):
  A single integer n with 1 <= n <= 3000.

On valid input: exit 42.  On invalid input: print a short message to stderr
and exit with code 1 (never 42).
"""
import re
import sys

MIN_N = 1
MAX_N = 3000


def main():
    data = sys.stdin.read()
    if not data.strip():
        sys.stderr.write("empty input\n")
        return 1

    tokens = data.split()
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer\n")
        return 1

    tok = tokens[0]
    if not re.fullmatch(r"[0-9]+", tok):
        sys.stderr.write("not a base-10 integer: %s\n" % tok)
        return 1

    n = int(tok)
    if not (MIN_N <= n <= MAX_N):
        sys.stderr.write("n out of range %d..%d: %d\n" % (MIN_N, MAX_N, n))
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
