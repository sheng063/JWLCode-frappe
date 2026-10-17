#!/usr/bin/env python3
"""Validator for the "多组乘法计算" (multiple multiplication) problem.

Statement format (authoritative problem.zh.tex):
    题目描述: 使用 cout 输出多组乘法计算的结果，每个运算结果占一行。
    输入格式: 无。程序不需要读取任何输入。
    输出格式: 输出三行，分别为 3 * 8、6 * 7、4 * 5 的计算结果。

Because the input format is explicitly "无" (none), the only valid input is
empty (or whitespace-only). Any non-whitespace content is invalid.

This is a no-input problem: there is no numeric range to enforce
(range not specified / not applicable).

Exits 42 on valid input, prints a short message to stderr and exits 1 on
invalid input.
"""

import sys


def main() -> None:
    data = sys.stdin.read()

    # A valid case has no program input at all. Allow blank/whitespace-only
    # input, which is how the judge invokes a no-input case.
    if data.strip() != "":
        sys.stderr.write(
            "ERROR: expected no input for this problem, but got non-whitespace content\n"
        )
        sys.exit(1)

    # Valid input: empty (no tokens).
    sys.exit(42)


if __name__ == "__main__":
    main()
