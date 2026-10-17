#!/usr/bin/env python3
"""Input validator for "求不同高度的大气压值".

Input format (per problem statement):
  A single line containing one real number h (100 <= h <= 2500),
  representing the mountain height in meters.

On valid input: exit 42.
On invalid input: print a short stderr message and exit 1 (never 42).
"""
import re
import sys

# A real number in standard decimal notation: optional sign, digits,
# optional fractional part.  No exponent, no exponent-only forms.
REAL_RE = re.compile(r'^[+-]?(\d+)(\.\d*)?$|^[+-]?\.\d+$')


def main():
    data = sys.stdin.read()

    # Allow surrounding empty input but require exactly one number token.
    tokens = data.strip().split()
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one real number\n")
        return 1

    token = tokens[0]
    if not REAL_RE.match(token):
        sys.stderr.write("malformed real number: %r\n" % token)
        return 1

    # Could be a huge value that overflows float; reject non-finite.
    try:
        h = float(token)
    except ValueError:
        sys.stderr.write("out-of-range real number: %r\n" % token)
        return 1

    if h != h or h in (float('inf'), float('-inf')):
        sys.stderr.write("non-finite real number: %r\n" % token)
        return 1

    if not (100.0 <= h <= 2500.0):
        sys.stderr.write("h out of range [100,2500]: %r\n" % token)
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
