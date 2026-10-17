#!/usr/bin/env python3
"""Input validator for the "数鸡兔" (counting chickens and rabbits) problem.

Input format (per problem.zh.tex):
  - A single line containing two space-separated integers: heads (tou) and
    feet (jiao).
  - Both quantities are within the range storable in a signed int, and the
    input is guaranteed to represent a valid (non-negative integer) solution.

The problem counts chickens (2 feet each) and rabbits (4 feet each):
    chickens + rabbits = tou
    2*chickens + 4*rabbits = jiao
which has a non-negative integer solution iff
    tou >= 0, jiao >= 0, jiao is even, and 2*tou <= jiao <= 4*tou.

On valid input this program exits with code 42. On any invalid input it prints
a short message to stderr and exits with code 1.
"""

import re
import sys

INT_MAX = 2147483647  # max value storable in a signed 32-bit int
INTEGER_RE = re.compile(rb"[0-9]+")  # non-negative integer literal only


def fail(msg):
    sys.stderr.write("invalid input: " + msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.buffer.read()

    # The statement requires exactly one line of content (trailing whitespace
    # is acceptable). Reject fully empty input and multi-line content.
    stripped = data.strip()
    if not stripped:
        fail("input is empty")
    if len(stripped.split(b"\n")) != 1:
        fail("expected a single line")

    # Exactly two whitespace-separated tokens and no extra tokens.
    tokens = stripped.split()
    if len(tokens) != 2:
        fail("expected exactly two integers, got %d token(s)" % len(tokens))

    # Each token must be a plain non-negative integer literal (reject signs,
    # underscores, floats, etc.).
    hunhe = []
    for tok in tokens:
        if not INTEGER_RE.fullmatch(tok):
            fail("token is not a non-negative integer: %r" % tok)
        hunhe.append(int(tok))

    tou, jiao = hunhe[0], hunhe[1]

    # Both quantities must be within the range storable in a signed int.
    if tou > INT_MAX:
        fail("heads out of int range: %d" % tou)
    if jiao > INT_MAX:
        fail("feet out of int range: %d" % jiao)

    # Guaranteed to have a non-negative integer chicken/rabbit solution.
    #   rabbits = (jiao - 2*tou) / 2 must be a non-negative integer
    #   chickens = tou - rabbits must be non-negative
    if jiao % 2 != 0:
        fail("odd number of feet cannot come from chickens/rabbits")
    if jiao < 2 * tou:
        fail("too few feet for the given number of heads")
    if jiao > 4 * tou:
        fail("too many feet for the given number of heads")

    sys.exit(42)


if __name__ == "__main__":
    main()
