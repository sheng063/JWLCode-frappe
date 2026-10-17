#!/usr/bin/env python3
import sys

def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)

data = sys.stdin.read().split()
if len(data) != 2:
    fail("expected exactly 2 integers, got %d" % len(data))
try:
    a = int(data[0]); b = int(data[1])
except ValueError:
    fail("expected integer tokens")
INT_MIN = -2147483648
INT_MAX = 2147483647
if not (INT_MIN <= a <= INT_MAX):
    fail("a out of int range")
if not (INT_MIN <= b <= INT_MAX):
    fail("b out of int range")
sys.exit(42)
