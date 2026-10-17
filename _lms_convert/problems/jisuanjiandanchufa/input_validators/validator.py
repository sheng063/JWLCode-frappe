#!/usr/bin/env python3
"""Input validator for 计算简单除法.

The statement declares 输入格式: 无  (there is no input).
Therefore valid stdin is empty or whitespace-only; any non-whitespace
content violates the statement and must be rejected.
"""
import sys


def main():
    data = sys.stdin.buffer.read()
    if data.strip() == b"":
        sys.exit(42)
    sys.stderr.write("invalid input: expected no input (empty/whitespace-only stdin)\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
