#!/usr/bin/env python3
"""Validate the input for "四则运算小练".

The statement specifies:
  - Input is one line containing two space-separated integers a and b.
  - Constraints: 0 < a < 100, 0 < b < 100.

On valid input the validator exits with code 42; on invalid input it prints a
short message to stderr and exits with code 1.
"""

import re
import sys

# A well-formed base-10 integer, with an optional leading sign (matches how
# C++ stream extraction parses an integer).
INT_RE = re.compile(r"^[+-]?[0-9]+$")


def main():
    data = sys.stdin.read()

    # The input must contain exactly two whitespace-separated integer tokens.
    tokens = data.split()
    if len(tokens) != 2:
        sys.stderr.write(
            "expected exactly 2 integers (a and b) on one line, got %d token(s)\n"
            % len(tokens)
        )
        sys.exit(1)

    vals = []
    for t in tokens:
        if not INT_RE.match(t):
            sys.stderr.write("not a valid base-10 integer: %r\n" % t)
            sys.exit(1)
        vals.append(int(t))

    a, b = vals

    # Enforce exactly the constraints stated in the problem: 0 < a < 100 and
    # 0 < b < 100 (so both a and b lie in [1, 99]).
    if not (0 < a < 100):
        sys.stderr.write("a out of range (must satisfy 0 < a < 100): %d\n" % a)
        sys.exit(1)
    if not (0 < b < 100):
        sys.stderr.write("b out of range (must satisfy 0 < b < 100): %d\n" % b)
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
