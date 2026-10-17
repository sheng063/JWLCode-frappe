#!/usr/bin/env python3
"""Validator for problem '试一试逻辑运算' (shiyishiluojiyunsuan).

Input format (per statement):
  A line of four integers a, b, x, y separated by whitespace, with
  -2^31 <= a, b, x, y <= 2^31 - 1.

On valid input exits with code 42. On invalid input prints a short
message to stderr and exits with code 1 (never 42).
"""

import sys

LO = -(2 ** 31)
HI = (2 ** 31) - 1


def parse_int_token(tok):
    """Return the integer value of tok, or None if not a base-10 integer."""
    s = tok
    if s.startswith('+'):
        s = s[1:]
    if s == '':
        return None
    neg = False
    if s.startswith('-'):
        neg = True
        s = s[1:]
    if s == '' or not s.isdigit():
        return None
    val = int(tok)                      # Python handles arbitrary precision.
    if neg and val > HI:                # cannot be more negative than LO
        return None
    return val


def main():
    data = sys.stdin.read()

    # The input must be exactly four whitespace-separated integer tokens.
    tokens = data.split()
    if len(tokens) != 4:
        sys.stderr.write("expected exactly 4 integers\n")
        return 1

    vals = []
    for tok in tokens:
        v = parse_int_token(tok)
        if v is None:
            sys.stderr.write("malformed integer: %s\n" % tok)
            return 1
        if v < LO or v > HI:
            sys.stderr.write("integer out of range [-2^31, 2^31-1]: %s\n" % tok)
            return 1
        vals.append(v)

    return 42


if __name__ == "__main__":
    sys.exit(main())
