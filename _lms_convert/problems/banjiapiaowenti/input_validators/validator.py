#!/usr/bin/env python3
import sys
import re
from decimal import Decimal

# A well-formed decimal/float literal.  n is "一个浮点数" per the statement.
# Accepts optional sign, optional fraction digits, and optional exponent.
FLOAT_RE = re.compile(r'^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$')

LO = Decimal('0.5')
HI = Decimal('3.0')


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def main():
    raw = sys.stdin.buffer.read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        fail('input is not valid UTF-8')

    tokens = text.split()
    if len(tokens) != 1:
        fail('expected exactly one floating-point number')

    tok = tokens[0]
    if not FLOAT_RE.match(tok):
        fail(f'invalid floating-point literal: {tok!r}')

    try:
        val = Decimal(tok)
    except Exception as e:
        fail(f'cannot parse number {tok!r}: {e}')

    if not (LO <= val <= HI):
        fail(f'value out of range [{LO}, {HI}]: {tok}')

    sys.exit(42)


if __name__ == '__main__':
    main()
