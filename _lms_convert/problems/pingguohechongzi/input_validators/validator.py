#!/usr/bin/env python3
"""Input validator for problem '苹果和虫子' (apple & worm).

Reads stdin and validates that it exactly matches the statement:

  输入格式: 三个整数 n x y
    n >= 1   (苹果总数)
    x >= 1   (虫子吃掉一个苹果所需小时数)
    y >= 0   (经过小时数)

Upper bounds are NOT specified in the statement, so this validator only
requires each value to be a well-formed base-10 integer that fits in a
signed 64-bit integer (the maximum the reference solution needlessly
relies on for overflow-safe arithmetic).  No narrow made-up range is
imposed.

On valid input exits with code 42; on invalid input prints a short stderr
message and exits with code 1 (never 42).
"""

import sys

LONG_LONG_MAX = 2**63 - 1
LONG_LONG_MIN = -(2**63)

def is_well_formed_int(tok: str) -> bool:
    """A well-formed base-10 integer: optional sign followed by digits.

    A bare '+'/'-' or empty string is not well formed; leading zeroes are
    allowed (e.g. '007')."""
    if not tok:
        return False
    if tok[0] in "+-":
        body = tok[1:]
    else:
        body = tok
    if body == "" or not body.isdigit():
        return False
    return True


def main() -> int:
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 3:
        sys.stderr.write("invalid: expected exactly 3 integers (n x y), got %d\n" % len(tokens))
        return 1

    vals = []
    for i, tok in enumerate(tokens):
        if not is_well_formed_int(tok):
            sys.stderr.write("invalid: token %d '%s' is not a well-formed integer\n" % (i + 1, tok))
            return 1
        v = int(tok)
        if v < LONG_LONG_MIN or v > LONG_LONG_MAX:
            sys.stderr.write("invalid: token %d '%s' overflows signed 64-bit\n" % (i + 1, tok))
            return 1
        vals.append(v)

    n, x, y = vals
    if n < 1:
        sys.stderr.write("invalid: n must be >= 1, got %d\n" % n)
        return 1
    if x < 1:
        sys.stderr.write("invalid: x must be >= 1, got %d\n" % x)
        return 1
    if y < 0:
        sys.stderr.write("invalid: y must be >= 0, got %d\n" % y)
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
