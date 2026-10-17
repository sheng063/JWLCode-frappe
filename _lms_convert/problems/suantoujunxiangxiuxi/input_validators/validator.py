#!/usr/bin/env python3
"""Input validator for 蒜头君想休息 (suantoujunxiangxiuxi).

Input format (from problem_statement/problem.zh.tex):
  a single integer n, with 0 <= n <= 16, representing hours studied today.

Output rule:
  n >= 8  -> "rest"
  n <  8  -> "work"

Valid input exits with code 42. Invalid input prints a short message to
stderr and exits with code 1.
"""
import sys


def main():
    data = sys.stdin.read()
    s = data.strip()
    if s == "":
        print("error: empty input", file=sys.stderr)
        sys.exit(1)

    tokens = s.split()
    if len(tokens) != 1:
        print("error: expected exactly one integer, got %d tokens" % len(tokens), file=sys.stderr)
        sys.exit(1)

    tok = tokens[0]
    # A single non-negative base-10 integer (0 <= n <= 16, per the statement).
    if not tok.isdigit():
        print("error: '%s' is not a non-negative integer" % tok, file=sys.stderr)
        sys.exit(1)

    n = int(tok)
    if not (0 <= n <= 16):
        print("error: n=%d out of range [0,16]" % n, file=sys.stderr)
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
