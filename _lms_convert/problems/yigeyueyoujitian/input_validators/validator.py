#!/usr/bin/env python3
"""Validate input for "一个月有几天".

Input format (problem statement): two integers
    y  (1600 <= y <= 3000)  -- the year
    m  (1 <= m <= 12)       -- the month
printed on a single line, separated by whitespace.
"""

import sys


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 2:
        fail("expected exactly two integers: year and month")

    try:
        y = int(tokens[0])
        m = int(tokens[1])
    except ValueError:
        fail("year and month must be well-formed base-10 integers")

    if not (1600 <= y <= 3000):
        fail("year out of range: 1600 <= y <= 3000")
    if not (1 <= m <= 12):
        fail("month out of range: 1 <= m <= 12")

    sys.exit(42)


if __name__ == "__main__":
    main()
