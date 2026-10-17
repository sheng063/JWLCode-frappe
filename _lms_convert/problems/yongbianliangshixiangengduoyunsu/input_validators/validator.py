#!/usr/bin/env python3
"""Input validator for the '用变量实现更多运算' problem.

The problem statement declares there is NO input (本题没有输入, the square's
side is fixed at 2.5).  Therefore the only valid input is empty or whitespace
only; any non-whitespace content is malformed.

On valid input this program exits with code 42.
On invalid input it prints a short message to stderr and exits with code 1.
"""

import sys


def main() -> int:
    data = sys.stdin.read()
    # A valid input for this no-input problem contains nothing but whitespace.
    # strip() removes all leading/trailing whitespace; if anything remains the
    # input carries non-whitespace characters and is therefore invalid.
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
