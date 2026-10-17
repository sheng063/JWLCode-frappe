#!/usr/bin/env python3
"""Input validator for problem "幸运的数字".

Statement input format: a single integer x with 100 <= x <= 999.

On valid input this script exits with code 42.  On invalid input it prints a
short message to stderr and exits with code 1 (never 42).
"""
import re
import sys

# The statement only constrains x to the range 100..999, so the validator
# accepts any well-formed decimal integer whose numeric value lies in that
# range.  No other numeric bound is stated by the problem.
PATTERN = re.compile(r"[0-9]+")


def validate(data: str) -> int:
    s = data.strip()
    if not s:
        sys.stderr.write("empty input; expected a single integer\n")
        return 1
    if PATTERN.fullmatch(s) is None:
        sys.stderr.write("input is not a well-formed non-negative integer\n")
        return 1
    x = int(s)
    if x < 100 or x > 999:
        sys.stderr.write("%d out of range 100..999\n" % x)
        return 1
    return 42


def main() -> None:
    sys.exit(validate(sys.stdin.read()))


if __name__ == "__main__":
    main()
