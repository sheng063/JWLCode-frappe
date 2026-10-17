#!/usr/bin/env python3
"""Validator for problem 'shuzipaixu' (数字排序).

Input format (authoritative, problem.zh.tex):
  Input consists of a single line containing three integers
  a, b, c separated by spaces. Each value is within the range
  that an 'int' type variable can store (standard signed 32-bit int:
  -2147483648 .. 2147483647).

On valid input: exit 42.
On invalid input: print a short stderr message and exit 1.
"""
import sys
import re

INT_MIN = -2147483648
INT_MAX = 2147483647

_TOKEN = re.compile(r'[+-]?\d+')


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 3:
        sys.stderr.write(
            "invalid: expected exactly 3 integers, got %d tokens\n" % len(tokens))
        return 1

    for tok in tokens:
        if not _TOKEN.fullmatch(tok):
            sys.stderr.write("invalid: token %r is not a base-10 integer\n" % tok)
            return 1
        val = int(tok)
        if val < INT_MIN or val > INT_MAX:
            sys.stderr.write(
                "invalid: value %s outside int storage range\n" % tok)
            return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
