#!/usr/bin/env python3
"""Input validator for problem '绝对值排序' (absolute-value sorting).

Statement:
  Input contains exactly 2 distinct integers within the C++ `int` range
  (i.e. signed 32-bit: [-2147483648, 2147483647]), separated by a space.

Rules enforced:
  * exactly two whitespace-separated tokens
  * each token is a well-formed base-10 integer (optional leading minus sign)
  * each value fits in signed 32-bit int range
  * the two integers are distinct (as stated)

On valid input, exits 42. Otherwise prints a short message to stderr and
exits 1 (never 42).
"""
import re
import sys

INT_MIN = -2147483648
INT_MAX = 2147483647

TOKEN_RE = re.compile(r'-?[0-9]+')


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 2:
        fail("expected exactly 2 integers separated by whitespace, got %d token(s)"
             % len(tokens))

    values = []
    for t in tokens:
        if not TOKEN_RE.fullmatch(t):
            fail("token is not a well-formed base-10 integer: %r" % t)
        v = int(t)
        if v < INT_MIN or v > INT_MAX:
            fail("integer out of the stated int range (%d..%d): %s"
                 % (INT_MIN, INT_MAX, t))
        values.append(v)

    if values[0] == values[1]:
        fail("the two integers must be distinct: %d and %d" % (values[0], values[1]))

    sys.exit(42)


if __name__ == "__main__":
    main()
