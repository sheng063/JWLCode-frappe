#!/usr/bin/env python3
# Validator for "考试等级划分" (Exam Grade Classification).
# Input: a single integer fen (percentage score), 0 <= fen <= 100.
import sys

def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)

tokens = sys.stdin.read().split()
if len(tokens) != 1:
    fail("expected exactly 1 integer, got %d" % len(tokens))
try:
    fen = int(tokens[0])
except ValueError:
    fail("expected an integer token")
if not (0 <= fen <= 100):
    fail("fen out of range 0..100")
sys.exit(42)
