#!/usr/bin/env python3
"""Validator for "约数还是倍数" (divisor or multiple).

Statement guarantees:
  - Input is a single line containing two space-separated integers a, b.
  - a and b have a divisor-multiple relationship (one divides the other).
  - Both fit in the range an int type variable can store.

Rules enforced here:
  - Exactly one non-empty line of input, containing exactly two base-10 integers.
  - Both integers within signed 32-bit int range.
  - A divisor-multiple relationship (a % b == 0 or b % a == 0, divisor nonzero).
  - The quotient actually printed must not divide by zero (so the reference
    implementation never crashes on a case the validator accepts).

On valid input this exits with status 42; otherwise it prints a short message to
stderr and exits with status 1 (never 42).
"""

import sys

INT_MIN = -2147483648
INT_MAX = 2147483647


def fail(msg):
    sys.stderr.write("invalid input: " + msg + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()

    # Enforce "only one line of input": after dropping a trailing newline there
    # must be no further line breaks.
    lines = data.split("\n")
    # remove a single trailing empty element produced by a final '\n'
    if lines and lines[-1].strip() == "":
        lines.pop()
    # also tolerate a single leading empty element from a leading newline? The
    # statement says one line, so we are strict and reject extra blank lines.
    if len(lines) != 1:
        fail("expected exactly one line of input")

    toks = lines[0].split()
    if len(toks) != 2:
        fail("expected exactly two space-separated integers")

    try:
        a = int(toks[0])
        b = int(toks[1])
    except ValueError:
        fail("non-integer token")

    if not (INT_MIN <= a <= INT_MAX and INT_MIN <= b <= INT_MAX):
        fail("integer(s) outside the range int can store")

    # divisor-multiple relationship: one of them divides the other.
    ok = False
    if a != 0 and b % a == 0:
        ok = True
    if b != 0 and a % b == 0:
        ok = True
    if not ok:
        fail("a and b are not in a divisor-multiple relationship")

    # The quotient that the statement directs to be printed must be well defined
    # (its divisor must be non-zero), otherwise the reference solution would
    # crash.  a sets b/a when a <= b, and a/b when a > b.
    divisor = b if a > b else a
    if divisor == 0:
        fail("the printed quotient would divide by zero")

    sys.exit(42)


if __name__ == "__main__":
    main()
