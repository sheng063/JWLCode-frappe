#!/usr/bin/env python3
"""Validator for problem "tiaojianfenzhixiaojie" (C1 · 条件分支小结).

Input format (from the statement): three integers a b c.
No numeric range is given in the statement; the only requirement is that each
value is a well-formed base-10 integer that the reference solution (which reads
into signed 64-bit) can safely parse, i.e. it fits in a signed 64-bit int.

On valid input  -> sys.exit(42)
On invalid input -> print a short message to stderr and exit 1.
"""

import sys

INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1


def is_s64_token(s):
    """Return True iff s is a well-formed base-10 integer in signed 64-bit range."""
    if s == "":
        return False
    # Optional single sign; the rest must be decimal digits.
    body = s[1:] if s[0] in "+-" else s
    if body == "":
        return False
    if not all(ch in "0123456789" for ch in body):
        return False
    try:
        val = int(s, 10)
    except ValueError:
        return False
    return INT64_MIN <= val <= INT64_MAX


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 3:
        sys.stderr.write("expected exactly 3 integers\n")
        sys.exit(1)
    for tok in tokens:
        if not is_s64_token(tok):
            sys.stderr.write("invalid integer token: %r\n" % tok)
            sys.exit(1)

    # Nothing else is constrained by the statement (no numeric bound given).
    sys.exit(42)


if __name__ == "__main__":
    main()
