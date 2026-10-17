#!/usr/bin/env python3
"""Validator for the '长方形的面积' (Rectangle Area) problem.

Input format (from the statement):
  "输入一个两个浮点数 l 和 w，分别表示长方形的长和宽。"
  i.e. exactly two base-10 floating-point numbers l and w (length and width).

The statement gives NO numeric range for l or w ("range not specified").
So the validator only enforces:
  - exactly two well-formed base-10 floating-point numbers,
  - each representable as a finite double (so the reference solution's
    multiplication cannot turn a finite parse into inf via representation),
  - separated by any whitespace (spaces, tabs, newlines), as usual for
    >> based readers.

On valid input the validator exits with code 42.
On invalid input it prints a short message to stderr and exits with code 1.
"""
import re
import sys

# A plain base-10 floating-point number, optional sign, optional decimal
# point (handles "3", "1.5", ".5", "5.", "-2.5", "+0.25"). No exponent
# notation is used, to stay within the plain-decimal style of the sample.
_NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


def main():
    data = sys.stdin.read()
    if not data.strip():
        sys.stderr.write("error: expected two floating-point numbers, got empty input\n")
        return 1

    tokens = data.split()
    if len(tokens) != 2:
        sys.stderr.write(
            "error: expected exactly two floating-point numbers, got %d token(s)\n"
            % len(tokens)
        )
        return 1

    for tok in tokens:
        if not _NUM_RE.match(tok):
            sys.stderr.write("error: not a well-formed base-10 number: %r\n" % tok)
            return 1
        try:
            v = float(tok)
        except ValueError:
            sys.stderr.write("error: cannot parse number: %r\n" % tok)
            return 1
        # Reject infinities/NaN produced by representing huge digit strings.
        if v != v:  # NaN
            sys.stderr.write("error: NaN is not a valid number: %r\n" % tok)
            return 1
        if v in (float("inf"), float("-inf")):
            sys.stderr.write("error: number out of double range: %r\n" % tok)
            return 1

    sys.exit(42)


if __name__ == "__main__":
    sys.exit(main())
