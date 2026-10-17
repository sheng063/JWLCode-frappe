#!/usr/bin/env python3
"""Validator for the "选礼物" problem.

Reads stdin. The input EXACTLY matches the statement format:
  line 1: h   (100 <= h <= 150)  -- the character's height
  line 2: x1 x2 x3  (1 <= xi <= 240)  -- the three gift heights

On valid input, exits with code 42.
On invalid input, prints a short message to stderr and exits with code 1.
"""
import sys


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 4:
        sys.stderr.write("error: expected exactly 4 integers (h, x1, x2, x3)\n")
        return 1

    try:
        h = int(tokens[0])
        xs = [int(t) for t in tokens[1:4]]
    except ValueError:
        sys.stderr.write("error: input contains non-integer tokens\n")
        return 1

    if not (100 <= h <= 150):
        sys.stderr.write("error: h out of range [100,150]: %d\n" % h)
        return 1

    for i, v in enumerate(xs, 1):
        if not (1 <= v <= 240):
            sys.stderr.write("error: x%d out of range [1,240]: %d\n" % (i, v))
            return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
