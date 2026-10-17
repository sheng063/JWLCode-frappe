#!/usr/bin/env python3
"""Validator for "数学考试".

Input: a single integer n, the exam score.
Constraint (from statement): 1 <= n <= 100.

On valid input exits with code 42; on invalid input prints a short
message to stderr and exits with code 1.
"""
import sys


def main() -> None:
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 1:
        sys.stderr.write("error: expected exactly one integer\n")
        sys.exit(1)

    tok = tokens[0]
    try:
        n = int(tok)
    except ValueError:
        sys.stderr.write("error: token is not a base-10 integer: %s\n" % tok)
        sys.exit(1)

    if n < 1 or n > 100:
        sys.stderr.write("error: score out of range [1,100]: %d\n" % n)
        sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
