#!/usr/bin/env python3
"""Input validator for problem 'kaixuedianli' (开学典礼).

Statement (authoritative, problem.zh.tex):
  Input is a single line with two positive integers.  n satisfies
  0 <= n <= 10000, and m satisfies 10000 <= m <= 100000.  They denote
  n new students plus m other students in the school.

The validator tokenizes stdin on whitespace and requires exactly two
well-formed base-10 integers meeting those ranges.  On valid input it
exits 42; on invalid input it prints a short message to stderr and exits 1.
"""
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 2:
        sys.stderr.write("expected exactly two integers\n")
        return 1
    for tok in tokens:
        if not tok.isdigit():
            sys.stderr.write("not a non-negative integer: %r\n" % tok)
            return 1
    n = int(tokens[0])
    m = int(tokens[1])
    if not (0 <= n <= 10000):
        sys.stderr.write("n out of range [0, 10000]: %d\n" % n)
        return 1
    if not (10000 <= m <= 100000):
        sys.stderr.write("m out of range [10000, 100000]: %d\n" % m)
        return 1
    sys.exit(42)


if __name__ == "__main__":
    main()
