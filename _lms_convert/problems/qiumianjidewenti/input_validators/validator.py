#!/usr/bin/env python3
"""Input validator for "求面积的问题" (calculate the area).

Statement input format:
  line 1: a single character, either 'r' (rectangle) or 't' (triangle)
  line 2: two real numbers m and n (for a rectangle: length, width; for a
          triangle: base, height), with 0.0 < m <= 100.0.

The statement gives NO numeric bound for n (range not specified); any
well-formed base-10 real number is allowed, subject only to the overflow
bound the solution genuinely needs (the resulting area must be a finite
double).

On valid input: exit code 42.
On invalid input: a short stderr message and exit code 1 (never 42).
"""
import math
import re
import sys

# A well-formed base-10 real number (matches "3.0", "2.1", ".5", "-7.5", "1e5",
# "+3.0", ...). Rejects hex floats, "nan", "inf", words, etc.
_RE_NUM = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")


def die(msg):
    sys.stderr.write("invalid input: " + msg + "\n")
    sys.exit(1)


def main():
    text = sys.stdin.read()
    # Trim trailing whitespace/blank lines; the input must be exactly two lines.
    text = text.rstrip()
    if not text:
        die("empty input")
    lines = text.split("\n")
    if len(lines) != 2:
        die("expected exactly 2 lines, found %d" % len(lines))

    # Line 1: a single character 'r' or 't'.
    c = lines[0].strip()
    if len(c) != 1:
        die("line 1 must be a single character")
    if c not in ("r", "t"):
        die("line 1 must be 'r' (rectangle) or 't' (triangle)")

    # Line 2: exactly two real numbers m and n.
    toks = lines[1].split()
    if len(toks) != 2:
        die("line 2 must contain exactly two real numbers")
    for t in toks:
        if not _RE_NUM.match(t):
            die("'%s' is not a well-formed base-10 real number" % t)

    m = float(toks[0])
    n = float(toks[1])
    if not math.isfinite(m):
        die("m is not finite")
    if not math.isfinite(n):
        die("n is not finite")

    # Stated bound for m: 0.0 < m <= 100.0.
    if not (0.0 < m <= 100.0):
        die("m must satisfy 0.0 < m <= 100.0")

    # n has no stated numeric bound (range not specified). The solver computes
    # m*n for the rectangle, which must stay finite (overflow bound).
    if not math.isfinite(m * n):
        die("area would overflow")

    sys.exit(42)


if __name__ == "__main__":
    main()
