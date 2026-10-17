#!/usr/bin/env python3
"""Validator for the no-input problem "shuonihao" (说你好).

The problem statement supplies no input at all: the program simply prints
"hello".  Therefore the only well-formed input is an empty stdin (or stdin
containing only whitespace, which carries no data).

On valid input this validator exits with code 42.  On malformed input it
prints a short message to stderr and exits with code 1 (never 42).
"""

import sys


def main() -> int:
    data = sys.stdin.buffer.read()

    # The statement specifies no input and no numeric bounds; accept any
    # whitespace-only stdin as an empty input, and reject everything else.
    if data.strip() == b"":
        sys.exit(42)

    sys.stderr.write("invalid input: expected empty (whitespace-only) input\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
