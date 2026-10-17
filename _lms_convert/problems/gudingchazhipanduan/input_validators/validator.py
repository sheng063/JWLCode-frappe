#!/usr/bin/env python3
"""Input validator for "固定差值判断".

The statement requires:
  - a single line with 5 space-separated positive integers
  - each integer is strictly less than 10000 (i.e. 1 <= x <= 9999)
  - the five integers are strictly increasing

On valid input exit(42); otherwise write a message to stderr and exit(1).
"""

import sys


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()

    # The statement demands a single line of input.
    if data.count("\n") > 1:
        fail("input must consist of a single line")

    tokens = data.split()
    if len(tokens) != 5:
        fail("expected exactly 5 integers, got %d" % len(tokens))

    vals = []
    for tok in tokens:
        # Well-formed base-10 non-negative integer string only.
        if not tok.isdigit():
            fail("token is not a base-10 integer: %r" % tok)
        v = int(tok)
        # Positive integers less than 10000.
        if v < 1:
            fail("integer must be positive, got %d" % v)
        if v >= 10000:
            fail("integer must be less than 10000, got %d" % v)
        vals.append(v)

    # The five integers are strictly increasing.
    for i in range(1, len(vals)):
        if vals[i] <= vals[i - 1]:
            fail("integers must be strictly increasing at position %d" % (i + 1))

    sys.exit(42)


if __name__ == "__main__":
    main()
