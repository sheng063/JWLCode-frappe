#!/usr/bin/env python3
"""Validator for 蒜园门票.

Input format (per problem statement):
  A single positive integer n, the number of tickets purchased.

Constraints (per problem statement):
  The input number is within the int range (signed 32-bit), and it is a
  positive integer, so 1 <= n <= 2147483647.

On valid input: exit 42.
On invalid input: print a short message to stderr and exit 1.
"""
import sys


def main():
    data = sys.stdin.read()
    # The whole input must be exactly one integer, possibly surrounded by
    # leading/trailing whitespace (e.g. a trailing newline).
    fields = data.split()
    if len(fields) != 1:
        sys.stderr.write("error: expected exactly one integer\n")
        sys.exit(1)

    token = fields[0]

    # Positive integer: digits only, no sign, no decimal point.
    if not token.isdigit():
        sys.stderr.write("error: input is not a positive integer\n")
        sys.exit(1)

    n = int(token)

    if n <= 0:
        sys.stderr.write("error: must be a positive integer\n")
        sys.exit(1)

    # Constraint: input number is within the (signed 32-bit) int range.
    if n > 2147483647:
        sys.stderr.write("error: exceeds int range\n")
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
