#!/usr/bin/env python3
"""Validator for the "按要求输出" (output by instruction) problem.

Input format (exactly, per the statement):
    The input contains one character x, which must be one of 'a', 'b', or 'c'.

The single character may be surrounded by whitespace (e.g. a trailing newline),
but there must be exactly one character token and no additional content.
"""

import sys


def main() -> None:
    data = sys.stdin.read()
    stripped = data.strip()

    if stripped == "":
        sys.stderr.write("ERROR: expected exactly one character (got empty input)\n")
        sys.exit(1)

    if len(stripped) != 1:
        sys.stderr.write(
            "ERROR: expected exactly one character, found %d characters\n" % len(stripped)
        )
        sys.exit(1)

    ch = stripped
    if ch not in ("a", "b", "c"):
        sys.stderr.write(
            "ERROR: invalid character %r (must be one of 'a', 'b', 'c')\n" % ch
        )
        sys.exit(1)

    # Valid input: exactly one of 'a', 'b', 'c'.
    sys.exit(42)


if __name__ == "__main__":
    main()
