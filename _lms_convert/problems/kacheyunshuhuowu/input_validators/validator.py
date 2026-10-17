#!/usr/bin/env python3
"""Validate the input for problem '卡车运输货物'.

Statement constraints:
  - Input is a single integer m with 1 <= m <= 1000.
  - It is guaranteed that m is a multiple of 10.

On valid input: exit 42. On invalid input: print a short message to stderr
and exit 1 (never 42).
"""
import re
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 1:
        sys.stderr.write("error: expected exactly one integer\n")
        return 1

    tok = tokens[0]

    # Well-formed base-10 integer (no sign, no leading '+/-', digits only).
    if not re.fullmatch(r"\d+", tok):
        sys.stderr.write("error: input is not a well-formed base-10 integer\n")
        return 1

    m = int(tok)

    if not (1 <= m <= 1000):
        sys.stderr.write("error: m out of range (1 <= m <= 1000)\n")
        return 1

    if m % 10 != 0:
        sys.stderr.write("error: m is not a multiple of 10\n")
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
