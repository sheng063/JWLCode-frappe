#!/usr/bin/env python3
"""Validator for the problem 蒜头君上班 (legacy-icpc).

Statement input format: a single line containing one base-10 integer, the
distance to the company in meters.
The problem statement gives NO numeric bound for the distance, so this
validator enforces only:
  * exactly one integer token on stdin (one line, no extra values)
  * the token is a well-formed base-10 integer (optional leading '+'/'-')
  * it fits in the signed 64-bit range the reference C++ solution reads into
    (long long), which is the overflow bound the solution genuinely needs.

Valid input exits with code 42; invalid input prints a short message on
stderr and exits with code 1 (never 42).
"""

import re
import sys

INT_RE = re.compile(r"^[+-]?\d+$")
SIGNED_64_MIN = -(2 ** 63)
SIGNED_64_MAX = 2 ** 63 - 1


def main():
    data = sys.stdin.read()

    # Exactly one integer token must be present. Empty / whitespace-only input
    # is invalid (the statement always supplies one integer).
    tokens = data.split()
    if len(tokens) != 1:
        sys.stderr.write("expected exactly one integer on stdin\n")
        return 1

    tok = tokens[0]
    if not INT_RE.match(tok):
        sys.stderr.write("token is not a well-formed base-10 integer\n")
        return 1

    try:
        value = int(tok, 10)
    except ValueError:
        sys.stderr.write("token is not a valid base-10 integer\n")
        return 1

    if value < SIGNED_64_MIN or value > SIGNED_64_MAX:
        sys.stderr.write("integer out of signed 64-bit range\n")
        return 1

    return 42


if __name__ == "__main__":
    sys.exit(main())
