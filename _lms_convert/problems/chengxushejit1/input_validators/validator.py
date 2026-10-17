#!/usr/bin/env python3
"""Validate input for the '程序设计 T1' (case-toggle) problem.

Statement format:
  The input is exactly one letter of the English alphabet. If it is an
  uppercase letter (A-Z) the answer is its lowercase form; if it is a
  lowercase letter (a-z) the answer is its uppercase form.

No numeric range is stated in the problem: a single alphabetic character is
the only value the input can take (range not specified / not applicable).

Exits 42 on valid input, prints a short message to stderr and exits 1 on
invalid input.
"""

import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if not tokens:
        sys.stderr.write("input is empty\n")
        sys.exit(1)

    if len(tokens) != 1:
        sys.stderr.write("expected exactly one letter, got %d token(s)\n" % len(tokens))
        sys.exit(1)

    tok = tokens[0]
    if len(tok) != 1:
        sys.stderr.write("expected a single letter, got '%s'\n" % tok)
        sys.exit(1)

    if not (('a' <= tok <= 'z') or ('A' <= tok <= 'Z')):
        sys.stderr.write("input is not an English letter: '%s'\n" % tok)
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
