#!/usr/bin/env python3
"""Input validator for '蒜头君吃苹果'.

Input format (from problem.zh.tex):
  Line 1: a decimal m (0.0 <= m <= 10.0)  -- apples eaten per minute
  Line 2: an integer n (1 <= n <= 100)    -- number of minutes

On valid input:
    sys.exit(42)
On invalid input:
    print a short message to stderr and sys.exit(1)
"""
import re
import sys

# m is literally described as a decimal (小数), so it must carry a decimal
# point with at least one digit on each side and no sign (range is 0..10).
DECIMAL_RE = re.compile(r"^[0-9]+\.[0-9]+$")
INTEGER_RE = re.compile(r"^[0-9]+$")


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    # The statement gives two lines, each holding one value. Tokenize on
    # whitespace so the check is line/whitespace agnostic.
    tokens = data.split()
    if len(tokens) != 2:
        fail("expected exactly 2 whitespace-separated tokens, got %d" % len(tokens))

    m_str, n_str = tokens

    # ---- m: decimal in [0.0, 10.0] ----
    if not DECIMAL_RE.match(m_str):
        fail("m is not a well-formed decimal: %r" % m_str)

    # Value bounds: exact decimal comparison against 0.0 and 10.0.
    # Represent m as an integer numerator over 10^d to stay exact.
    ip, fp = m_str.split(".")
    d = len(fp)
    num = int(ip) * (10 ** d) + int(fp)
    # m >= 0.0
    if num < 0:
        fail("m is out of range (m < 0.0): %s" % m_str)
    # m <= 10.0
    if num > 10 * (10 ** d):
        fail("m is out of range (m > 10.0): %s" % m_str)

    # ---- n: integer in [1, 100] ----
    if not INTEGER_RE.match(n_str):
        fail("n is not a well-formed non-negative integer: %r" % n_str)
    n = int(n_str)
    if n < 1 or n > 100:
        fail("n is out of range (1 <= n <= 100): %s" % n_str)

    sys.exit(42)


if __name__ == "__main__":
    main()
