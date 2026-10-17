#!/usr/bin/env python3
"""Validator for the "肥胖问题" (feipangwenti) problem.

Input format (per the authoritative statement):
  A single line with two space-separated integers m and h,
  40 <= m <= 120, 140 <= h <= 200.

A valid input exits with code 42; any invalid input prints a message to
stderr and exits with code 1.
"""
import re
import sys

INT_RE = re.compile(r"^[+-]?\d+$")

M_MIN, M_MAX = 40, 120
H_MIN, H_MAX = 140, 200


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 2:
        sys.stderr.write("invalid: expected exactly two integers (m and h)\n")
        return 1

    for tok in tokens:
        if not INT_RE.match(tok):
            sys.stderr.write("invalid: token '%s' is not a well-formed integer\n" % tok)
            return 1

    m = int(tokens[0])
    h = int(tokens[1])

    if not (M_MIN <= m <= M_MAX):
        sys.stderr.write("invalid: m=%d out of range [%d,%d]\n" % (m, M_MIN, M_MAX))
        return 1
    if not (H_MIN <= h <= H_MAX):
        sys.stderr.write("invalid: h=%d out of range [%d,%d]\n" % (h, H_MIN, H_MAX))
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
