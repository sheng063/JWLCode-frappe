#!/usr/bin/env python3
"""Validate input for problem 'mainaitang' (buy milk candies).

Input format (from problem_statement/problem.zh.tex):
  Two whitespace-separated numbers:
    n : a positive integer, 10 <= n <= 100
    m : a floating-point number, 1.0 <= m <= 10.0

On valid input exit 42; on invalid input print a short stderr message and
exit 1 (never 42).
"""
import re
import sys

INT_RE = re.compile(r"[0-9]+")
FLOAT_RE = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?")


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 2:
        sys.stderr.write("expected exactly two whitespace-separated numbers\n")
        return 1

    n_str, m_str = tokens[0], tokens[1]

    # n: positive integer with 10 <= n <= 100
    if not INT_RE.fullmatch(n_str):
        sys.stderr.write("n is not a non-negative integer\n")
        return 1
    n = int(n_str)
    if not (10 <= n <= 100):
        sys.stderr.write("n out of range [10, 100]\n")
        return 1

    # m: floating-point number with 1.0 <= m <= 10.0
    if not FLOAT_RE.fullmatch(m_str):
        sys.stderr.write("m is not a well-formed floating-point number\n")
        return 1
    m = float(m_str)
    if not (1.0 <= m <= 10.0):
        sys.stderr.write("m out of range [1.0, 10.0]\n")
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
