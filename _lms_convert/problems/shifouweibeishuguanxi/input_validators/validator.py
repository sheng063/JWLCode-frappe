#!/usr/bin/env python3
"""Input validator for problem 'shifouweibeishuguanxi'.

Statement constraints (authoritative):
  - Input is one line containing two integers a, b.
  - 0 < b < a < 1000
  - a and b are integers, distinct, with a > b.

On valid input: sys.exit(42).
On invalid input: print a short message to stderr and exit with code 1.
"""
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 2:
        sys.stderr.write("expected exactly two integers on one line\n")
        return 1

    try:
        a = int(tokens[0])
        b = int(tokens[1])
    except ValueError:
        sys.stderr.write("a and b must be integers\n")
        return 1

    # Explicit statement bound: 0 < b < a < 1000.
    if not (0 < b < a < 1000):
        sys.stderr.write("constraint violated: must satisfy 0 < b < a < 1000\n")
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
