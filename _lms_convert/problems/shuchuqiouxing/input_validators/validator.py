#!/usr/bin/env python3
"""Validator for problem 输出奇偶性 (shuchuqiouxing).

Input format (from problem.zh.tex):
    A single line containing one integer shu, which fits in a C++ int
    (32-bit signed) range.

On valid input, exit with code 42.  On invalid input, print a short message
to stderr and exit with code 1 (never 42).
"""
import re
import sys

# The statement states the value fits in an int (32-bit signed).
INT_MIN = -2147483648
INT_MAX = 2147483647

INT_RE = re.compile(r'^[+-]?\d+$')


def main():
    data = sys.stdin.read()

    if data.strip() == "":
        sys.stderr.write("error: empty input\n")
        return 1

    tokens = data.split()
    if len(tokens) != 1:
        sys.stderr.write("error: expected exactly one integer\n")
        return 1

    token = tokens[0]
    if not INT_RE.match(token):
        sys.stderr.write("error: not a base-10 integer: %s\n" % token)
        return 1

    value = int(token)
    if value < INT_MIN or value > INT_MAX:
        sys.stderr.write("error: value out of int range: %d\n" % value)
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
