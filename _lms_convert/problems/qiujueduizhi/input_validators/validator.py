#!/usr/bin/env python3
"""输入校验器：求绝对值。

输入格式（problem.zh.tex）：
    输入包含一个整数 n（-100 <= n <= 100）。
  即：stdin 必须恰好包含一个格式良好的十进制整数 n，且 -100 <= n <= 100。

校验规则：
  - 整数必须恰好是一个（允许一个可选正负号 + 若干十进制数字）；
  - 值必须落在 [-100, 100] 区间内（题目在输入格式中显式给出的约束）。

合法输入：sys.exit(42)；
非法输入：向 stderr 打印一句说明并 sys.exit(1)。
"""

import re
import sys

INT_RE = re.compile(r"[+-]?\d+\Z")
LOWER = -100
UPPER = 100


def main():
    data = sys.stdin.read()

    tokens = data.split()
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer, got %d token(s)\n" % len(tokens))
        return 1

    s = tokens[0]
    if not INT_RE.match(s):
        sys.stderr.write("not a well-formed base-10 integer: %r\n" % s)
        return 1

    try:
        n = int(s)
    except ValueError:
        sys.stderr.write("integer out of parseable range: %r\n" % s)
        return 1

    if not (LOWER <= n <= UPPER):
        sys.stderr.write("n=%d out of range [%d, %d]\n" % (n, LOWER, UPPER))
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
