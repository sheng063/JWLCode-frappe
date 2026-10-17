#!/usr/bin/env python3
"""Input validator for the 星期问题 problem.

The statement specifies exactly one integer x with 0 <= x <= 6.
On valid input: exit 42.  On invalid input: print a short message to stderr
and exit with code 1 (never 42).
"""
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer\n")
        sys.exit(1)

    tok = tokens[0]
    try:
        x = int(tok, 10)
    except ValueError:
        sys.stderr.write("not a base-10 integer: %s\n" % tok)
        sys.exit(1)

    if x < 0 or x > 6:
        sys.stderr.write("x out of range 0..6: %d\n" % x)
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
