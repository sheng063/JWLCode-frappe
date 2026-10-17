#!/usr/bin/env python3
"""Input validator for problem 'youfei' (邮费).

Statement (authoritative, problem.zh.tex):
  Input is a single positive integer x with 1 <= x <= 50, denoting the
  weight (kg) of the package to be mailed.

The validator tokenizes stdin on whitespace and requires exactly one
well-formed base-10 integer restricted to the stated range.  On valid
input it exits 42; on invalid input it prints a short message to stderr
and exits 1 (never 42).
"""
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer\n")
        return 1

    tok = tokens[0]
    if not tok.isdigit():
        sys.stderr.write("not a positive base-10 integer: %r\n" % tok)
        return 1

    x = int(tok)
    if not (1 <= x <= 50):
        sys.stderr.write("x out of stated range [1, 50]: %d\n" % x)
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
