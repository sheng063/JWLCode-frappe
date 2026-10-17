#!/usr/bin/env python3
"""Validate input for problem '年龄的计算'.

The statement gives one line with two integers:
  n: 蒜头君's age    (10 <= n <= 20)
  x: the difference  (5 <= x <= 20)
On valid input exit 42; on invalid input print a short message to stderr
and exit 1.
"""
import sys


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 2:
        fail("expected exactly 2 integers, got %d token(s)" % len(tokens))

    try:
        n = int(tokens[0])
        x = int(tokens[1])
    except ValueError:
        fail("a token is not a well-formed base-10 integer")

    if not (10 <= n <= 20):
        fail("n out of range [10,20]: %d" % n)
    if not (5 <= x <= 20):
        fail("x out of range [5,20]: %d" % x)

    sys.exit(42)


if __name__ == "__main__":
    main()
