#!/usr/bin/env python3
"""Validate input for the problem '小数的除法'.

The statement specifies:
  * the input is two different floating-point numbers `a`, `b`;
  * the range constraints 1 <= a <= 100 and 1 <= b <= 100.

Every rule enforced here comes directly from the statement. Nothing else is
invented (no extra numeric ranges):
  * exactly two whitespace-delimited tokens;
  * each token is a well-formed base-10 floating-point literal;
  * each token parses to a finite double (the reference solution computes a / b
    and prints it, so a non-finite value would not be a valid input);
  * 1 <= a <= 100 and 1 <= b <= 100;
  * a != b  (the two floating-point numbers must be different).

On valid input this exits with code 42; on invalid input it prints a short
message to stderr and exits with code 1.
"""
import math
import re
import sys

# A well-formed base-10 floating-point literal:
#   optional sign, then a mantissa with at least one digit (before and/or after
#   an optional decimal point), and an optional exponent part.
FLOAT_RE = re.compile(r'^[+-]?(?:(?:\d+\.?\d*)|(?:\.\d+))(?:[eE][+-]?\d+)?$')


def validate():
    toks = sys.stdin.read().split()
    if len(toks) != 2:
        return "expected exactly two floating-point numbers, got %d token(s)" % len(toks)

    vals = []
    for t in toks:
        if not FLOAT_RE.match(t):
            return "not a well-formed base-10 floating-point number: %r" % t
        try:
            v = float(t)
        except ValueError:
            return "unparseable floating-point number: %r" % t
        if not math.isfinite(v):
            return "number not representable as a finite double: %r" % t
        vals.append(v)

    a, b = vals
    if not (1.0 <= a <= 100.0):
        return "a out of stated range [1,100]: %r" % a
    if not (1.0 <= b <= 100.0):
        return "b out of stated range [1,100]: %r" % b
    if a == b:
        return "a and b must be different numbers, got %r and %r" % (a, b)
    return None


def main():
    err = validate()
    if err is not None:
        print("invalid input: " + err, file=sys.stderr)
        return 1
    return 42


if __name__ == "__main__":
    sys.exit(main())
