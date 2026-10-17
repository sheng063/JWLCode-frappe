#!/usr/bin/env python3
"""Validator for 整除与取模的应用 (cross-composed two-digit numbers).

Input (per statement):
  One line with two integers separated by spaces: the two-digit number of
  蒜头君 (Garlic) and the two-digit number of 花椰妹 (Broccoli).
  Each input is a two-digit number, 10 <= x <= 99.

Valid input -> exit 42. Invalid input -> stderr message and exit 1.
"""
import sys
import re


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()

    # The statement gives exactly two integers on one line. Reject extra/missing.
    tokens = data.split()
    if len(tokens) != 2:
        fail("expected exactly two integers")

    for tok in tokens:
        if not re.fullmatch(r"[0-9]+", tok):
            fail("token is not a well-formed base-10 integer")

    a, b = int(tokens[0]), int(tokens[1])

    # "二位数字": each value is a two-digit number, 10 <= x <= 99.
    if not (10 <= a <= 99):
        fail("first number out of range: 10 <= x <= 99")
    if not (10 <= b <= 99):
        fail("second number out of range: 10 <= x <= 99")

    sys.exit(42)


if __name__ == "__main__":
    main()
