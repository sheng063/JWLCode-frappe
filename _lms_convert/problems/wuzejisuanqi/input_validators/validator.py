#!/usr/bin/env python3
"""Input validator for the "五则计算器" (five-operation calculator) problem.

Input format (as stated):
  a op b
where a and b are integers and op is one of +, -, *, /, % — exactly three
whitespace-separated tokens, in that order.

The statement does NOT declare a numeric range for a or b. To avoid inventing
a constraint, this validator only checks structure (exactly three tokens, a
valid operator, both operands are base-10 integers) and that the operands are
representable in the 64-bit signed integer type the accepted solution uses
(so multiplication cannot silently overflow). Division/modulo by zero are
undefined and rejected. On valid input the validator exits with code 42; any
invalid input exits with code 1.
"""

import sys

# 64-bit signed integer bound (accepted solution uses long long).
MIN_OPERAND = -9223372036854775808
MAX_OPERAND = 9223372036854775807
OPERATORS = ("+", "-", "*", "/", "%")


def fail(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


def main():
    data = sys.stdin.read()
    tokens = data.split()

    if len(tokens) != 3:
        fail("expected exactly 3 tokens (a op b), got %d" % len(tokens))

    a_str, op, b_str = tokens

    if op not in OPERATORS:
        fail("invalid operator: %r" % op)

    try:
        a = int(a_str, 10)
    except ValueError:
        fail("operand a is not an integer: %r" % a_str)
    try:
        b = int(b_str, 10)
    except ValueError:
        fail("operand b is not an integer: %r" % b_str)

    if a < MIN_OPERAND or a > MAX_OPERAND:
        fail("a out of 64-bit signed range")
    if b < MIN_OPERAND or b > MAX_OPERAND:
        fail("b out of 64-bit signed range")

    if op in ("/", "%") and b == 0:
        fail("division/modulo by zero (op=%s, b=0)" % op)

    sys.exit(42)


if __name__ == "__main__":
    main()
