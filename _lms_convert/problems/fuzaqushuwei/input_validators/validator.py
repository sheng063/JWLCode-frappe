#!/usr/bin/env python3
"""Validator for 复杂取数位 (complex take digits).

Input (per statement):
  A single line containing an integer n, a three-digit number (100 <= n <= 999).

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
    # Three-digit number, 100 <= n <= 999 (explicitly stated constraint).
    if not (100 <= n <= 999):
        fail("n out of range: 100 <= n <= 999")

    sys.exit(42)


if __name__ == "__main__":
    main()
