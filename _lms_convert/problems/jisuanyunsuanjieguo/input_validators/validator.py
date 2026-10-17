#!/usr/bin/env python3
"""Validator for the '计算运算结果' problem.

The problem statement declares there is NO input: the program must not read
anything from stdin.  Therefore the only valid input is empty or whitespace
only.  Any non-whitespace content is malformed.

On valid input this exits 42; otherwise it prints a short message to stderr
and exits 1.
"""
import sys


def main():
    data = sys.stdin.read()
    # Trim leading/trailing whitespace; if nothing remains the input is valid.
    if data.strip() == "":
        sys.exit(42)
    sys.stderr.write("invalid input: expected no input, got non-whitespace data\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
