#!/usr/bin/env python3
"""Input validator for "用整型变量存储实数".

Input format: exactly one real number m on stdin (whitespace-only around it is
permitted). It must be a well-formed base-10 real number. The problem statement
gives no explicit numeric bound, so the only additional constraint enforced is
the genuine type/overflow bound the reference solution needs: the truncated
integer part of m must fit in a signed 32-bit int (the solution does
`int n = (int)m`).

On valid input exits 42; otherwise prints a short stderr message and exits 1.
"""
import re
import sys
from decimal import Decimal, InvalidOperation

INT_MIN = -2147483648
INT_MAX = 2147483647

# A well-formed base-10 real number: optional sign, integer/fractional digits,
# optional exponent. Matches the entire (whitespace-stripped) input.
NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def main():
    data = sys.stdin.read()
    s = data.strip()

    if not s:
        sys.stderr.write("error: empty input\n")
        return 1

    if not NUM_RE.match(s):
        sys.stderr.write("error: input is not a single well-formed real number\n")
        return 1

    try:
        d = Decimal(s)
    except InvalidOperation:
        sys.stderr.write("error: cannot parse number\n")
        return 1

    if not d.is_finite():
        sys.stderr.write("error: non-finite value\n")
        return 1

    # int(Decimal) truncates toward zero, matching the C++ `(int)m` cast.
    ip = int(d)
    if ip < INT_MIN or ip > INT_MAX:
        sys.stderr.write("error: integer part out of signed 32-bit int range\n")
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
