#!/usr/bin/env python3
"""Input validator for 贪吃蛇吃苹果 (tanchishechipingguo).

The problem statement specifies the input:
  - A single line with three integers n, x, y.
  - Each of n, x, y is a non-negative integer not exceeding 10^5.
  - It is guaranteed that y <= n*x.

Valid input must consist of exactly three base-10 non-negative integers, each in
[0, 10^5], satisfying y <= n*x. On valid input the validator prints nothing and
exits with code 42; on any malformed input it prints a short message to stderr
and exits with code 1 (never 42).
"""

import sys

MAX_VALUE = 100000  # "不超过 10^5"


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 3:
        sys.stderr.write("expected exactly 3 integers\n")
        return 1

    values = []
    for tok in tokens:
        # Well-formed non-negative base-10 integer (digits only, no sign).
        if not tok.isdigit():
            sys.stderr.write("non-integer token: %r\n" % tok)
            return 1
        values.append(int(tok))

    n, x, y = values

    for v in values:
        if v > MAX_VALUE:
            sys.stderr.write("value %d exceeds 10^5\n" % v)
            return 1

    # x, y, n are non-negative by construction (isdigit). Enforce the stated
    # guarantee y <= n*x.
    if y > n * x:
        sys.stderr.write("violates guarantee y <= n*x\n")
        return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
