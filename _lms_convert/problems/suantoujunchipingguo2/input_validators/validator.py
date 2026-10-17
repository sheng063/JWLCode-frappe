#!/usr/bin/env python3
"""Validate input for the problem '蒜头君吃苹果2'.

The statement specifies:
  * first line:  a real number m (0.0 <= m <= 10.0)   -- apples eaten per minute
  * second line: an integer n (1 <= n <= 100)         -- contest time (minutes)

Exactly two whitespace-delimited tokens are expected.

Enforced here are exactly the bounds given in the statement.  m must be a
well-formed non-negative base-10 decimal within [0.0, 10.0]; n must be a
well-formed base-10 integer within [1, 100].  No bounds beyond those stated
are imposed: in particular the number of fractional digits of m and the exact
magnitude of m*n are not constrained by the statement, and the reference
solution multiplies m by n exactly (fixed-point string arithmetic), so any
decimal precision for m is representable.

On valid input this exits with code 42; on invalid input it prints a short
message to stderr and exits with code 1.
"""
import re
import sys

# A well-formed non-negative base-10 decimal literal: at least one digit, with
# an optional fraction part (no sign, no exponent -- the statement gives m as
# a plain real number like "0.6").
REAL_RE = re.compile(r'^(\d+(\.\d*)?|\.\d+)$')
INT_RE = re.compile(r'^-?\d+$')


def validate():
    toks = sys.stdin.read().split()
    if len(toks) != 2:
        return "expected exactly 2 tokens (m and n), got %d" % len(toks)
    m, n = toks[0], toks[1]

    if not REAL_RE.match(m):
        return "m is not a well-formed non-negative decimal: %r" % m
    try:
        mv = float(m)
    except ValueError:
        return "m is not parseable as a number: %r" % m
    if not (0.0 <= mv <= 10.0):
        return "m out of range [0.0, 10.0]: %r" % m

    if not INT_RE.match(n):
        return "n is not a well-formed integer: %r" % n
    nv = int(n)
    if not (1 <= nv <= 100):
        return "n out of range [1, 100]: %d" % nv

    return None


def main():
    err = validate()
    if err is not None:
        print("invalid input: " + err, file=sys.stderr)
        return 1
    return 42


if __name__ == "__main__":
    sys.exit(main())
