#!/usr/bin/env python3
"""Validator for the '验一验关系表达式' (relation expression) problem.

Input must be exactly two base-10 integers a and b separated by whitespace,
satisfying -2^31 <= a, b <= 2^31 - 1.

Exits 42 on valid input, 1 (with a short stderr message) on invalid input.
"""
import re
import sys

# Exact bounds given in the statement: -2^31 <= a, b <= 2^31 - 1.
LOW = -(1 << 31)
HIGH = (1 << 31) - 1

data = sys.stdin.read()
if not data.strip():
    sys.stderr.write("error: empty input\n")
    sys.exit(1)

tokens = data.split()
if len(tokens) != 2:
    sys.stderr.write("error: expected exactly 2 integers, got %d token(s)\n" % len(tokens))
    sys.exit(1)

for tok in tokens:
    # Each token must be a well-formed base-10 integer (optional leading sign).
    if not re.fullmatch(r"[+-]?\d+", tok):
        sys.stderr.write("error: %r is not a base-10 integer\n" % tok)
        sys.exit(1)
    val = int(tok)
    if val < LOW or val > HIGH:
        sys.stderr.write("error: %s out of range [-2^31, 2^31 - 1]\n" % tok)
        sys.exit(1)

sys.exit(42)
