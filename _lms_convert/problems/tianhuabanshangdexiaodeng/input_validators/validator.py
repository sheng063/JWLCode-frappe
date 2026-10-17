#!/usr/bin/env python3
"""Validator for problem "天花板上的小灯".

Input format (per problem_statement/problem.zh.tex):
  Two space-separated integers a b, where
    1 <= a <= 100000  and  1 <= b <= 100000.

On valid input, exit 42. On malformed / out-of-range input, print a short
message to stderr and exit 1 (never 42).
"""
import re
import sys

INT_RE = re.compile(r"^[0-9]+$")

A_MIN, A_MAX = 1, 100000
B_MIN, B_MAX = 1, 100000


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    # The statement guarantees exactly two numbers, so empty/whitespace-only input
    # is malformed (this is not a "no-input" problem).
    if data is None:
        fail("empty input")
    tokens = data.split()
    if len(tokens) != 2:
        fail("expected exactly 2 space-separated integers")

    a_str, b_str = tokens

    if not INT_RE.match(a_str):
        fail("'%s' is not a well-formed non-negative base-10 integer" % a_str)
    if not INT_RE.match(b_str):
        fail("'%s' is not a well-formed non-negative base-10 integer" % b_str)

    a = int(a_str)
    b = int(b_str)

    if not (A_MIN <= a <= A_MAX):
        fail("a=%d out of range [%d, %d]" % (a, A_MIN, A_MAX))
    if not (B_MIN <= b <= B_MAX):
        fail("b=%d out of range [%d, %d]" % (b, B_MIN, B_MAX))

    sys.exit(42)


if __name__ == "__main__":
    main()
