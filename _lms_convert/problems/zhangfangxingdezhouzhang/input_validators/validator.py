#!/usr/bin/env python3
"""Validator for problem "zhangfangxingdezhouzhang" (长方形的周长).

Statement (authoritative: problem.zh.tex):
  Input: one line containing two floating-point numbers "chang" and "kuan"
         separated by whitespace.
  No numeric bounds on chang/kuan are given (range not specified), so only
  require each to be a well-formed base-10 floating-point number; also ensure
  the value is finite so the (double) solution produces a real number.

On valid input: sys.exit(42).
On invalid input: print a short message to stderr and exit 1 (never 42).
"""

import re
import sys

# A well-formed base-10 floating-point number:
#   optional sign, digits with optional decimal fraction, optional exponent.
# Examples accepted: "1.5", "2", ".5", "1.", "1e3", "-2.5e-2".
_NUM_RE = re.compile(r'^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$')


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 2:
        sys.stderr.write("expected exactly two floating-point numbers\n")
        return 1
    for tok in tokens:
        if not _NUM_RE.match(tok):
            sys.stderr.write("malformed number: %r\n" % tok)
            return 1
        try:
            value = float(tok)
        except ValueError:
            sys.stderr.write("not a floating-point number: %r\n" % tok)
            return 1
        # Reject NaN/Inf literals: the solution needs real, finite operands.
        if value != value or value in (float("inf"), float("-inf")):
            sys.stderr.write("non-finite number: %r\n" % tok)
            return 1
    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
