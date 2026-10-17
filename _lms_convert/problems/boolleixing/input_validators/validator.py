#!/usr/bin/env python3
"""Validator for a no-input problem.

The statement (problem.zh.tex) explicitly says the problem has no input.
The intended stdin is therefore empty; whitespace-only stdin is also accepted
(exit 42). Any non-whitespace content does not match the described input format
and is rejected (exit 1).
"""
import sys


def main():
    data = sys.stdin.read()
    if data.strip() == "":
        sys.exit(42)
    sys.stderr.write("Error: this problem has no input; "
                     "expected empty or whitespace-only stdin.\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
