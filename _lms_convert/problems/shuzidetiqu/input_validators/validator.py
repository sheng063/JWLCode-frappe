#!/usr/bin/env python3
"""Validate input for "数字的提取".

Input format:
  Line 1: integer n (10 <= n <= 99)
  Line 2: a single character c, one of 'a' or 'b'

Valid input: exit 42.
Invalid input: print a message to stderr, exit 1.
"""

import sys


def fail(msg):
    sys.stderr.write("invalid input: " + msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()

    # The statement specifies exactly two lines: n then c.
    # Require exactly two whitespace-separated tokens.
    tokens = data.split()
    if len(tokens) != 2:
        fail("expected exactly 2 tokens (n and c), got %d" % len(tokens))

    n_str, c = tokens

    # Validate n: a base-10 integer, 10 <= n <= 99.
    if not n_str.isdigit():
        fail("n is not a non-negative base-10 integer: %r" % n_str)
    n = int(n_str)
    if n < 10 or n > 99:
        fail("n out of range [10, 99]: %d" % n)

    # Validate c: a single character, 'a' or 'b'.
    if len(c) != 1:
        fail("c must be a single character, got %r" % c)
    if c != "a" and c != "b":
        fail("c must be 'a' or 'b', got %r" % c)

    sys.exit(42)


if __name__ == "__main__":
    main()
