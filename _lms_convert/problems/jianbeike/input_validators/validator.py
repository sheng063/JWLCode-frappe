#!/usr/bin/env python3
"""Validator for the "捡贝壳" (pick shells) problem.

Input format (from problem_statement/problem.zh.tex):
  A single real number: the weight a (jin) of each shell already in the box.
  Range: 0 < 2a <= 20, i.e. 0 < a <= 10.

Valid  -> sys.exit(42)
Invalid-> message on stderr + sys.exit(1)
"""
import math
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()

    # Exactly one token is allowed (no extra trailing tokens, no missing input).
    if len(tokens) != 1:
        print(
            "error: expected exactly one real number, got %d tokens" % len(tokens),
            file=sys.stderr,
        )
        return 1

    tok = tokens[0]

    # It must parse as a finite base-10 real number.
    try:
        a = float(tok)
    except ValueError:
        print("error: '%s' is not a valid real number" % tok, file=sys.stderr)
        return 1

    if not math.isfinite(a):
        print("error: number must be finite, got %r" % tok, file=sys.stderr)
        return 1

    # Stated bound: 0 < a <= 10.
    if not (0 < a <= 10):
        print("error: a must satisfy 0 < a <= 10, got %r" % tok, file=sys.stderr)
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
