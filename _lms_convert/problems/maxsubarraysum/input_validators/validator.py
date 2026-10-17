#!/usr/bin/env python3
import sys

N_MIN = 1
N_MAX = 200000
A_MIN = -1000000000
A_MAX = 1000000000


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def main():
    raw = sys.stdin.buffer.read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        fail('input is not valid UTF-8')

    toks = text.split()
    if not toks:
        fail('empty input')

    try:
        vals = [int(x) for x in toks]
    except ValueError:
        fail('non-integer token found')

    n = vals[0]
    if not (N_MIN <= n <= N_MAX):
        fail(f'n out of range: {n}')

    if len(vals) != n + 1:
        fail(f'expected {n} array elements, got {len(vals)-1}')

    for i, x in enumerate(vals[1:], 1):
        if not (A_MIN <= x <= A_MAX):
            fail(f'a[{i}] out of range: {x}')

    sys.exit(42)


if __name__ == '__main__':
    main()
