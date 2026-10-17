#!/usr/bin/env python3
"""Input validator for the no-input problem: 课前任务：打字练习.

The problem statement says there is NO input ("无输入").  The program reads
nothing and prints six fixed lines.  Valid stdin is therefore empty or
whitespace-only; any non-whitespace character is a violation of the stated
"no input" format.

Exit codes:
  42  valid (empty / whitespace-only stdin)
  1   invalid (any non-whitespace content)
"""
import sys


def main():
    data = sys.stdin.read()

    if data.strip() == "":
        sys.exit(42)
    else:
        sys.stderr.write(
            "invalid input: problem requires no input, "
            "but non-whitespace characters were provided\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
