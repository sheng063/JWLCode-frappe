#!/usr/bin/env python3
"""Validator for the "日历" (calendar) problem.

Input format: exactly one integer n.
Constraint: 0 < n < 100  (n is the number of days after today, Sunday).

A valid input contains exactly one whitespace-separated integer token whose
value satisfies 0 < n < 100. Any extra tokens, non-integer tokens, or values
outside the range are rejected.

On valid input the process exits with code 42. On invalid input a short
message is written to stderr and the process exits with code 1.
"""

import re
import sys

INT_RE = re.compile(r"^[+-]?[0-9]+$")


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 1:
        fail("expected exactly one integer token, got %d" % len(tokens))

    token = tokens[0]
    if not INT_RE.match(token):
        fail("token is not a valid integer: %r" % token)

    n = int(token)
    if not (0 < n < 100):
        fail("n=%d out of range: must satisfy 0 < n < 100" % n)

    sys.exit(42)


if __name__ == "__main__":
    main()
