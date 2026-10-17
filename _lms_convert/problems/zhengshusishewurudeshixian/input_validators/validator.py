#!/usr/bin/env python3
"""Validate input for 正数四舍五入的实现.

Format (from problem.zh.tex):
  A single line containing two positive numbers m and n separated by space.
  Output: two lines, the rounded (half-up) integer of m and n.

No numeric bound is stated for m and n (only that they are positive), so every
value is only required to be a well-formed base-10 positive decimal number.
A valid input makes this program exit with code 42; any malformed input prints
a short message to stderr and exits with code 1.
"""
import sys


def is_valid_positive_decimal(t):
    """Return True iff t is a base-10 positive number like '3', '1.2', '0.5'."""
    if not t:
        return False
    i = 0
    n = len(t)

    int_digits = 0
    while i < n and '0' <= t[i] <= '9':
        i += 1
        int_digits += 1
    if int_digits == 0:
        return False

    if i < n:
        if t[i] != '.':
            return False
        i += 1
        frac_digits = 0
        while i < n and '0' <= t[i] <= '9':
            i += 1
            frac_digits += 1
        if frac_digits == 0:
            return False

    if i != n:  # trailing garbage after the number
        return False

    # positive (value > 0): at least one non-zero digit among the digits
    if all(c == '0' for c in t if c != '.'):
        return False
    return True


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 2:
        sys.stderr.write("VALIDATOR: expected exactly two numbers, got %d\n" % len(tokens))
        sys.exit(1)
    for t in tokens:
        if not is_valid_positive_decimal(t):
            sys.stderr.write("VALIDATOR: invalid positive number: %r\n" % t)
            sys.exit(1)
    sys.exit(42)


if __name__ == "__main__":
    main()
