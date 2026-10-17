#!/usr/bin/env python3
"""Validator for the problem "图灵测试的简单模拟" (Turing test simulation).

The problem specifies 无输入 (no input): the program reads nothing and always
outputs "YES". Therefore the only valid stdin is empty or whitespace-only.

Constraints (from the statement): none on numeric values. Input format is "无输入".
- Valid (exit 42): empty or whitespace-only stdin.
- Invalid (exit 1): any non-whitespace content.
"""
import sys


def main():
    data = sys.stdin.buffer.read()
    # No-input problem: stdin must be empty or contain only whitespace.
    if data.strip() == b"":
        sys.exit(42)
    sys.stderr.write("invalid input: this problem takes no input "
                     "(expected empty or whitespace-only stdin)\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
