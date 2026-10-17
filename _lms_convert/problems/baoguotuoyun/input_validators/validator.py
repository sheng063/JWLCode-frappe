#!/usr/bin/env python3
"""Validator for the 包裹托运 problem.

Input: a single line containing one integer X (1 <= X <= 100).
On valid input exit 42; on invalid input print a short stderr message and
exit with code 1 (never 42).
"""
import re
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()

    # The statement specifies exactly one integer on a single line. Reject any
    # extra whitespace-separated tokens.
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer\n")
        return 1

    tok = tokens[0]
    # A well-formed base-10 integer: only decimal digits. This rejects signs,
    # underscores, decimal points, and empty strings. Leading zeros are allowed
    # (they still denote a valid integer).
    if not re.fullmatch(r"\d+", tok):
        sys.stderr.write("X is not a well-formed integer\n")
        return 1

    try:
        x = int(tok)
    except ValueError:
        sys.stderr.write("X is not a well-formed integer\n")
        return 1

    if x < 1 or x > 100:
        sys.stderr.write("X out of range [1,100]\n")
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
