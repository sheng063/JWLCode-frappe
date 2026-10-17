#!/usr/bin/env python3
"""Validator for 实现蜗牛爬树问题.

Input: a single line of three integers n, a, b separated by whitespace.

Constraints enforced (only what the statement explicitly states):
  * exactly three integers on the input
  * each integer is well-formed base-10 and fits in a signed 32-bit int
  * a > b
  * n - a is an integer multiple of (a - b)

On valid input: exits with code 42.
On invalid input: prints a short message to stderr and exits with code 1.
"""

import sys

INT_MIN = -2147483648
INT_MAX = 2147483647


def parse_int(tok):
    """Return the integer value of tok if it is a well-formed base-10 integer, else None."""
    if not tok:
        return None
    # allow an optional single leading sign
    body = tok[1:] if tok[0] in "+-" else tok
    if not body or not body.isdigit():
        return None
    try:
        return int(tok)
    except ValueError:
        return None


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 3:
        sys.stderr.write("expected exactly three integers\n")
        return 1

    vals = []
    for tok in tokens:
        v = parse_int(tok)
        if v is None:
            sys.stderr.write("not a base-10 integer: %s\n" % tok)
            return 1
        if v < INT_MIN or v > INT_MAX:
            sys.stderr.write("value out of int range: %s\n" % tok)
            return 1
        vals.append(v)

    n, a, b = vals

    if not (a > b):
        sys.stderr.write("constraint a > b violated\n")
        return 1

    if (n - a) % (a - b) != 0:
        sys.stderr.write("n - a is not an integer multiple of a - b\n")
        return 1

    # Valid input.
    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
