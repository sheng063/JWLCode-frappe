#!/usr/bin/env python3
"""Input validator for 蒜头君的信息卡 (C1 · 蒜头君的信息卡).

The problem statement specifies an empty input format:
  "输入格式: 无。程序不需要读取任何输入。"  (No input; the program reads nothing.)

Therefore the ONLY valid stdin is empty or whitespace-only content.
  - empty/whitespace-only stdin  -> exit 42  (valid)
  - any non-whitespace content   -> stderr message + exit 1  (invalid)
"""
import sys


def main():
    data = sys.stdin.read()
    if data.strip() == "":
        sys.exit(42)
    sys.stderr.write(
        "invalid: this problem takes no input, but non-whitespace content was supplied\n"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
