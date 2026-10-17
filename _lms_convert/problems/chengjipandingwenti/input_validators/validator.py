#!/usr/bin/env python3
"""Validate input for the '成绩判定问题' (grade grading) problem.

Statement format:
  The input is a single real number n with 0 <= n <= 100.

Exits 42 on valid input, prints a short message to stderr and exits 1 on
invalid input.
"""
import re
import sys

# A well-formed base-10 real number: optional integer part and optional
# fraction part after a '.'. No sign is allowed (the value is constrained to
# [0, 100]), and exponents/underscores are not accepted.
REAL_RE = re.compile(r"^[0-9]+(\.[0-9]+)?$")


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if not tokens:
        sys.stderr.write("input is empty\n")
        sys.exit(1)

    if len(tokens) != 1:
        sys.stderr.write("expected exactly one real number, got more tokens\n")
        sys.exit(1)

    tok = tokens[0]
    if not REAL_RE.match(tok):
        sys.stderr.write("malformed real number: %s\n" % tok)
        sys.exit(1)

    n = float(tok)

    # Only constraint stated in the problem: 0 <= n <= 100.
    if not (0.0 <= n <= 100.0):
        sys.stderr.write("out of range [0, 100]: %s\n" % tok)
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
