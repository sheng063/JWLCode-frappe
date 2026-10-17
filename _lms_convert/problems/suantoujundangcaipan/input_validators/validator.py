#!/usr/bin/env python3
"""Validator for problem "蒜头君当裁判".

Input format: a single integer n with 10 <= n <= 99.

Exit codes:
  42  -- input is valid.
  1   -- input is invalid (message printed to stderr).
"""
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 1:
        sys.stderr.write("error: expected exactly one integer\n")
        sys.exit(1)

    tok = tokens[0]
    if not tok.isdigit():
        sys.stderr.write("error: not a base-10 integer\n")
        sys.exit(1)

    try:
        n = int(tok)
    except ValueError:
        sys.stderr.write("error: not a base-10 integer\n")
        sys.exit(1)

    if not (10 <= n <= 99):
        sys.stderr.write("error: n must satisfy 10 <= n <= 99\n")
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
