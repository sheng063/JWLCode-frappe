#!/usr/bin/env python3
"""Input validator for the "一个月有多少天" (days in a month) problem.

The statement specifies exactly two integers on stdin:
    yue runnian
with the constraints:
    yue      : 1 <= yue <= 12
    runnian  : 1 == leap year, 0 == common year  (i.e. runnian in {0, 1})

On valid input this program exits with code 42.
On invalid input it prints a short message to stderr and exits with code 1.
"""

import sys


def fail(msg):
    sys.stderr.write("invalid input: " + msg + "\n")
    sys.exit(1)


def parse_int(s):
    """Parse a well-formed base-10 integer (optional leading sign, digits 0-9).

    Returns the integer value on success, or None if s is not a well-formed
    base-10 integer.  This deliberately checks ASCII digits only so that
    non-ASCII digit characters are rejected.
    """
    if s == "":
        return None
    i = 0
    if s[0] in "+-":
        i = 1
        if i == len(s):
            return None
    start = i
    while i < len(s):
        if not ("0" <= s[i] <= "9"):
            return None
        i += 1
    if i == start:
        return None
    return int(s)


def main():
    data = sys.stdin.read()
    tokens = data.split()
    if len(tokens) != 2:
        fail("expected exactly two integers, got %d token(s)" % len(tokens))

    yue_s, run_s = tokens

    yue = parse_int(yue_s)
    if yue is None:
        fail("'%s' is not a well-formed base-10 integer" % yue_s)

    runnian = parse_int(run_s)
    if runnian is None:
        fail("'%s' is not a well-formed base-10 integer" % run_s)

    if not (1 <= yue <= 12):
        fail("yue=%d out of range [1, 12]" % yue)

    if runnian not in (0, 1):
        fail("runnian=%d must be 0 or 1 (1 = leap year, 0 = common year)" % runnian)

    sys.exit(42)


if __name__ == "__main__":
    main()
