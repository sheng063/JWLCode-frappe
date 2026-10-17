#!/usr/bin/env python3
"""Validator for problem "程序改错".

The input is described as a single line containing three integers a, b, c
separated by spaces, with the constraint 1 <= a, b, c <= 10000.

On valid input this exits with code 42.  On invalid input it prints a short
message to stderr and exits with code 1.
"""
import sys


def is_int_token(tok):
    """Return True if tok is a well-formed base-10 integer (optional sign)."""
    if not tok:
        return False
    body = tok
    if body[0] in "+-":
        body = body[1:]
    return body.isdigit()


def main():
    data = sys.stdin.read()
    tokens = data.split()

    # Exactly three integers must be present.
    if len(tokens) != 3:
        sys.stderr.write("expected exactly 3 integers, got %d tokens\n" % len(tokens))
        sys.exit(1)

    vals = []
    for tok in tokens:
        if not is_int_token(tok):
            sys.stderr.write("malformed integer token: %r\n" % tok)
            sys.exit(1)
        vals.append(int(tok))

    # Statement constraint: 1 <= a, b, c <= 10000
    for v in vals:
        if not (1 <= v <= 10000):
            sys.stderr.write("value out of range [1, 10000]: %d\n" % v)
            sys.exit(1)

    sys.exit(42)


if __name__ == "__main__":
    main()
