#!/usr/bin/env python3
"""Input validator for the "今天会下雨吗" problem.

Input format (from the authoritative statement):
  A single integer H, the relative air humidity, with 0 <= H <= 100.

Valid input -> exit 42.
Invalid input -> a message on stderr and exit 1.
"""
import re
import sys

INT_RE = re.compile(r"^[+-]?\d+$")


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 1:
        sys.stderr.write("expected exactly 1 integer token, got %d\n" % len(tokens))
        return 1
    tok = tokens[0]
    if not INT_RE.match(tok):
        sys.stderr.write("token '%s' is not a well-formed base-10 integer\n" % tok)
        return 1
    h = int(tok, 10)
    if h < 0 or h > 100:
        sys.stderr.write("humidity %d out of allowed range [0, 100]\n" % h)
        return 1
    return 42


if __name__ == "__main__":
    sys.exit(main())
