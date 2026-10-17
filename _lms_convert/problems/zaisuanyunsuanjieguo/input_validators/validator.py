#!/usr/bin/env python3
"""Validator for "再算运算结果" (no-input problem).

The problem statement defines an empty input format ("程序不需要读取任何输入"),
so the only valid stdin is empty or contains whitespace only.
"""
import sys


def main():
    data = sys.stdin.read()

    # The statement requires no input at all; only blank/whitespace input is valid.
    if data.strip() == "":
        sys.exit(42)

    sys.stderr.write("invalid: expected no input (empty/whitespace only); got non-whitespace\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
