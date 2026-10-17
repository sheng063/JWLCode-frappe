#!/usr/bin/env python3
"""Validator for the "你好，小猫" problem.

Statement input format: "无" — the program does not need to read any input.
This is a no-input problem, so the only valid input is empty or whitespace-only.
Any non-whitespace content does not match the stated input format, so the
validator rejects it.

Exit codes:
  42  on valid (empty / whitespace-only) input
  1   on invalid input (stderr carries a short reason)
"""
import sys


def main():
    data = sys.stdin.buffer.read()
    # Decode tolerantly; any non-whitespace token is invalid for this no-input problem.
    text = data.decode("utf-8", errors="replace")
    if text.strip() != "":
        sys.stderr.write("error: expected no input, but found non-whitespace content\n")
        sys.exit(1)
    sys.exit(42)


if __name__ == "__main__":
    main()
