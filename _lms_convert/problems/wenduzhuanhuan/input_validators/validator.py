#!/usr/bin/env python3
import sys
import re

def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)

data = sys.stdin.read().split()

# Exactly two non-whitespace tokens: a unit letter and a temperature value.
if len(data) != 2:
    fail("expected exactly 2 tokens (unit and temperature), got %d" % len(data))

unit = data[0]
if unit not in ("C", "F"):
    fail("unit must be the letter 'C' or 'F', got %r" % unit)

num = data[1]
# Temperature is a plain base-10 number (integer or decimal), optional +/- sign.
if not re.fullmatch(r"[+-]?(\d+(\.\d*)?|\.\d+)", num):
    fail("temperature is not a well-formed number, got %r" % num)

try:
    val = float(num)
except ValueError:
    fail("temperature not parseable, got %r" % num)

# Statement bounds: -459.67 <= temperature <= 10000 (inclusive).
if not (-459.67 <= val <= 10000.0):
    fail("temperature %s out of stated range [-459.67, 10000]" % num)

sys.exit(42)
