#!/usr/bin/env python3
"""Input validator for problem `bianliangdeshengmingyushiyong`.

题目说明输入格式为：无。程序不需要读取任何输入。

Therefore the ONLY valid inputs are empty or whitespace-only:
  - no tokens at all
  - no non-whitespace characters

On valid stdin we exit with code 42; on invalid stdin we print a short
message to stderr and exit with a non-42 code (1).
"""

import sys


def main() -> int:
    data = sys.stdin.read()

    # A valid input for this no-input problem contains nothing but whitespace.
    # `strip()` removes all leading/trailing whitespace; if anything remains,
    # the input carries non-whitespace characters and is therefore invalid.
    if data.strip() != "":
        sys.stderr.write(
            "invalid input: this problem takes no input "
            "(expected empty or whitespace-only stdin)\n"
        )
        return 1

    # Valid input -> exit 42 per ICPC validator convention.
    return 42


if __name__ == "__main__":
    sys.exit(main())
