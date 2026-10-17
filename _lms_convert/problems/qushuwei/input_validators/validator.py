#!/usr/bin/env python3
"""Validator for 取数位 (take digits).

Input (per statement):
  A single integer n, a two-digit number (10 <= n <= 99).

Valid input -> exit 42. Invalid input -> stderr message and exit 1.
"""
import sys
import re


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()

    # The statement gives exactly one integer. Reject empty/extra tokens.
    tokens = data.split()
    if len(tokens) != 1:
        fail("expected exactly one integer")

    tok = tokens[0]
    if not re.fullmatch(r"[0-9]+", tok):
        fail("token is not a well-formed base-10 integer")

    n = int(tok)
    # Two-digit number, 10 <= n <= 99.
    if not (10 <= n <= 99):
        fail("n out of range: 10 <= n <= 99")

    sys.exit(42)


if __name__ == "__main__":
    main()
