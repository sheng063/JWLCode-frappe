#!/usr/bin/env python3
"""Validate input for 程序设计 T2 (shipping fee with coupon).

Input format (from the problem statement):
    A single line containing an integer X (1 <= X <= 100) and a character Y,
    where Y is exactly one of A, B, C.
        A: coupon that deducts half the shipping fee
        B: coupon that deducts 7 yuan
        C: no coupon used

On valid input, exits 42. On invalid input, prints a short message to stderr
and exits with code 1 (never 42).
"""

import re
import sys


def main():
    data = sys.stdin.read()

    # Strip trailing whitespace (newlines / spaces). The input is a single
    # logical line; we tolerate normal trailing newlines but nothing else.
    stripped = data.strip()
    if stripped == "":
        sys.stderr.write("validator: empty input\n")
        return 1

    # Exactly two whitespace-separated tokens are allowed. Any extra token
    # (an extra line, a repeated value, etc.) makes the input invalid.
    tokens = stripped.split()
    if len(tokens) != 2:
        sys.stderr.write(
            "validator: expected 2 tokens (weight and coupon), got %d\n"
            % len(tokens)
        )
        return 1

    weight_token, coupon_token = tokens

    # X must be a well-formed base-10 non-negative integer token.
    if not re.fullmatch(r"[0-9]+", weight_token):
        sys.stderr.write("validator: weight %r is not a base-10 integer\n"
                         % weight_token)
        return 1

    x = int(weight_token)
    # Statement bound: 1 <= X <= 100.
    if not (1 <= x <= 100):
        sys.stderr.write("validator: weight %d out of range [1, 100]\n" % x)
        return 1

    # Y must be exactly one of A, B, C (uppercase).
    if not re.fullmatch(r"[ABC]", coupon_token):
        sys.stderr.write("validator: coupon %r is not one of A, B, C\n"
                         % coupon_token)
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
