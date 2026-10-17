#!/usr/bin/env python3
"""Validator for problem 'chengxushejit3'.

Input format (per problem.zh.tex):
  Line 1: 'm p1'  where 0 < m <= 100 (strawberry weight), 1 < p1 <= 100 (price)
  Line 2: 'n p2'  where 0 < n <= 100 (mango weight),      1 < p2 <= 100 (price)

The discount rule is triggered by the total weight (m + n) >= 20, but the
validator only enforces the stated bounds on each value.

On valid input: exit 42.  On invalid input: print an error to stderr, exit 1.
"""

import sys


def err(msg):
    sys.stderr.write("invalid: " + msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 4:
        err("expected 4 integers (m p1 / n p2), got %d token(s)" % len(tokens))

    for t in tokens:
        if not t.isdigit():
            err("token %r is not a well-formed base-10 non-negative integer" % t)

    m, p1, n, p2 = (int(t) for t in tokens)

    if not (0 < m <= 100):
        err("m out of stated range (0 < m <= 100): %d" % m)
    if not (1 < p1 <= 100):
        err("p1 out of stated range (1 < p1 <= 100): %d" % p1)
    if not (0 < n <= 100):
        err("n out of stated range (0 < n <= 100): %d" % n)
    if not (1 < p2 <= 100):
        err("p2 out of stated range (1 < p2 <= 100): %d" % p2)

    sys.exit(42)


if __name__ == "__main__":
    main()
