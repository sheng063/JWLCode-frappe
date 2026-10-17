#!/usr/bin/env python3
"""Validate input for the "实现：角的个数" problem.

Format (as stated): a single integer n on its own line(s).
The problem statement gives no numeric bound for n, so we only require that n
is a well-formed base-10 integer plus the genuine 64-bit overflow bound the
reference solution needs: reading n as a signed 64-bit long long and computing
the answer n + 4 must not overflow (n + 4 must fit in a signed 64-bit integer).
"""
import sys

LLONG_MIN = -(2 ** 63)
LLONG_MAX = 2 ** 63 - 1
# n + 4 must be representable in a signed 64-bit integer.
N_MAX = LLONG_MAX - 4  # 9223372036854775803


def fail(msg):
    sys.stderr.write("invalid input: " + msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 1:
        fail("expected exactly one integer, got %d token(s)" % len(tokens))

    tok = tokens[0]
    body = tok
    if tok and tok[0] in ("+", "-"):
        body = tok[1:]
    if body == "" or not all(c in "0123456789" for c in body):
        fail("not a well-formed base-10 integer: %r" % tok)

    n = int(tok)
    if not (LLONG_MIN <= n <= N_MAX):
        fail("n=%d out of computation-safe 64-bit range" % n)

    sys.exit(42)


main()
