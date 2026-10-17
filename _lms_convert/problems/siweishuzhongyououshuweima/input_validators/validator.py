#!/usr/bin/env python3
"""Validate input for the "四位数中有偶数位吗" (four-digit has an even digit) problem.

Input format: exactly one four-digit positive integer n, with 1000 <= n <= 9999.
Valid input exits with code 42; invalid input prints a short message to stderr
and exits with code 1 (never 42).
"""
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()

    # The statement reads a single integer; exactly one token is allowed.
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer, got %d token(s)\n" % len(tokens))
        sys.exit(1)

    tok = tokens[0]

    # Must be a plain base-10 integer: ASCII digits only, no sign, no leading/trailing junk.
    if not tok or any(c < '0' or c > '9' for c in tok):
        sys.stderr.write("not a base-10 integer: %r\n" % tok)
        sys.exit(1)

    value = int(tok)

    # Statement constraint: n is a four-digit positive integer, 1000 <= n <= 9999.
    if not (1000 <= value <= 9999):
        sys.stderr.write("n=%d violates the stated constraint 1000<=n<=9999\n" % value)
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
