#!/usr/bin/env python3
"""Validator for "7 的奇倍数" (7's odd multiple).

Input format (from the authoritative statement):
  A single integer n with 0 <= n <= 100.

The statement describes reading "a positive integer n" but explicitly gives
the numeric bound 0 <= n <= 100; we enforce exactly that stated bound.

On valid input: exit 42. On invalid input: print a short message to stderr
and exit 1 (never 42).
"""

import re
import sys

TOKEN_RE = re.compile(r"[0-9]+")


def main():
    data = sys.stdin.read()
    tokens = data.split()

    # The statement supplies exactly one integer.
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer as input\n")
        sys.exit(1)

    tok = tokens[0]
    if not TOKEN_RE.fullmatch(tok):
        sys.stderr.write("n is not a well-formed non-negative integer\n")
        sys.exit(1)

    n = int(tok)
    if not (0 <= n <= 100):
        sys.stderr.write("n out of stated range [0, 100]\n")
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
