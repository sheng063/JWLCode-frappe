#!/usr/bin/env python3
"""Validator for 分段电费 (tiered electricity fee)."""
import re
import sys

# The statement only says n is a positive integer (no upper bound given).
# A 64-bit bound is genuinely needed so the C++ (long long) fee computation
# cannot overflow. The exact upper bound is not specified in the statement.
MAX_N = 10**18


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 1:
        print("invalid: expected exactly one integer token", file=sys.stderr)
        return 1
    tok = tokens[0]
    if not re.fullmatch(r"[0-9]+", tok):
        print("invalid: token is not a base-10 integer: %r" % (tok,), file=sys.stderr)
        return 1
    n = int(tok)
    if n < 1:
        print("invalid: n must be a positive integer (n >= 1)", file=sys.stderr)
        return 1
    if n > MAX_N:
        print("invalid: n exceeds the accepted bound (%d)" % MAX_N, file=sys.stderr)
        return 1
    sys.exit(42)


if __name__ == "__main__":
    main()
