#!/usr/bin/env python3
"""Validate input for the problem '输出保留3位小数的浮点数'.

The statement specifies: the input is a single floating-point number `shu`.
No numeric range is stated (the statement gives no bound on the magnitude),
so the only constraints enforced here are structural:
  * exactly one whitespace-delimited token,
  * it is a well-formed base-10 floating-point literal,
  * it is representable as a finite double (the reference solution reads a
    double and formats it with printf("%.3f"); a value that overflows double
    to inf would not be a valid rounding input).

On valid input this exits with code 42; on invalid input it prints a short
message to stderr and exits with code 1.
"""
import math
import re
import sys

# A well-formed base-10 floating-point literal:
#   optional sign, then a mantissa with at least one digit (before or after the
#   decimal point, which is optional), and an optional exponent part.
FLOAT_RE = re.compile(r'^[+-]?(?:(?:\d+\.?\d*)|(?:\.\d+))(?:[eE][+-]?\d+)?$')


def validate():
    data = sys.stdin.read()
    toks = data.split()
    if len(toks) != 1:
        return "expected exactly one floating-point number, got %d token(s)" % len(toks)
    tok = toks[0]
    if not FLOAT_RE.match(tok):
        return "not a well-formed base-10 floating-point number: %r" % tok
    try:
        val = float(tok)
    except ValueError:
        return "unparseable floating-point number: %r" % tok
    if not math.isfinite(val):
        return "number not representable as a finite double (out of range): %r" % tok
    return None


def main():
    err = validate()
    if err is not None:
        print("invalid input: " + err, file=sys.stderr)
        return 1
    return 42


if __name__ == "__main__":
    sys.exit(main())
