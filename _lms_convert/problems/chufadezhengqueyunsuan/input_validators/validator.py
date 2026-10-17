#!/usr/bin/env python3
"""Validator for the problem "除法的正确运算".

Input format (from problem_statement/problem.zh.tex):
    Two integers a b  (a is the dividend, b is the divisor).
    Both a and b are base-10 integers. No numeric bound is stated, so the
    only enforced bounds are that each integer is well-formed and fits in a
    signed 64-bit integer (the solution reads them as `long long`).

Valid inputs -> exit 42. Invalid inputs -> a message on stderr and exit 1.
"""
import re
import sys

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807

TOKEN_RE = re.compile(r"^[+-]?\d+$")


def fail(msg):
    sys.stderr.write("INVALID: " + msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 2:
        fail("expected exactly 2 integers, got %d token(s)" % len(tokens))

    for t in tokens:
        if not TOKEN_RE.match(t):
            fail("token '%s' is not a well-formed base-10 integer" % t)
        digits = t.lstrip("+-")
        if digits == "":
            fail("token '%s' has no digits" % t)
        n = int(t)
        if n < INT64_MIN or n > INT64_MAX:
            fail("integer '%s' is outside the signed 64-bit range" % t)

    # b may be 0: the statement explicitly defines the output for b == 0 (ERROR),
    # so it is a valid input.
    sys.exit(42)


if __name__ == "__main__":
    main()
