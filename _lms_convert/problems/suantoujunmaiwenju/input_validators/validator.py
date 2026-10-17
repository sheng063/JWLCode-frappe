#!/usr/bin/env python3
"""Validator for "蒜头君买文具" (Garlic buys stationery).

Input format   : three lines, each a positive integer:
                   line 1: n  (m < n <= 100)
                   line 2: m  (1 <= m <= 5)
                   line 3: k  (m*n < k <= 1000)
The statement guarantees k satisfies the boys/girls ratio, meaning there must
exist non-negative integers (b, g) with b + g = n and m*b + 2m*g = k, i.e.
k must be a multiple of m and g = k/m - n must be in [0, n].

On valid input: exit 42.  On invalid input: print a short stderr message and
exit 1 (never 42).
"""

import re
import sys

POS_INT = re.compile(r"[0-9]+\Z")


def fail(msg):
    sys.stderr.write(msg + "\n")
    return 1


def parse_pos_int(s):
    """Return a positive base-10 integer for s, or None if not well-formed."""
    if not POS_INT.match(s):
        return None
    return int(s)


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 3:
        return fail("Error: expected exactly 3 integers (n, m, k), got %d" % len(tokens))

    n = parse_pos_int(tokens[0])
    m = parse_pos_int(tokens[1])
    k = parse_pos_int(tokens[2])
    if n is None or m is None or k is None:
        return fail("Error: n, m, k must each be a positive base-10 integer")

    if not (1 <= m <= 5):
        return fail("Error: m out of range [1,5]: %d" % m)

    if not (m < n <= 100):
        return fail("Error: n out of range (m < n <= 100): n=%d m=%d" % (n, m))

    if not (m * n < k <= 1000):
        return fail("Error: k out of range (m*n < k <= 1000): k=%d m*n=%d" % (k, m * n))

    # The statement guarantees k admits a valid (boys, girls) split:
    #   g = k/m - n must be an integer >= 0   (requires k % m == 0)
    #   b = n - g must be >= 0                (requires g <= n)
    if k % m != 0:
        return fail("Error: k must be a multiple of m (k=%d m=%d)" % (k, m))

    g = k // m - n
    b = n - g
    if g < 0 or b < 0:
        return fail("Error: k yields no valid boys/girls split (g=%d b=%d n=%d)" % (g, b, n))

    return 42


if __name__ == "__main__":
    sys.exit(main())
