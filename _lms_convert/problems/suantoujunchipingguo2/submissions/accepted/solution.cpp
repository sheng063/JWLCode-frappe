// 蒜头君吃苹果2
//
// Garlic Jun eats m apples per minute for n minutes. Apples that are not
// completely finished count as zero, so the number of apples actually eaten is
// floor(m * n).  The task is to print 1 (odd) or 0 (even) accordingly.
//
// To stay exactly correct we avoid floating point (e.g. 0.3*10 rounds to
// 2.9999... in double and would wrongly floor to 2 instead of 3).  Instead we
// interpret m as a fixed-point decimal and multiply exactly with integer
// string arithmetic.
//
//   m = mantissa / 10^k       (mantissa = m's digits with the point removed,
//                              k = number of fractional digits)
//   m * n = (mantissa * n) / 10^k
//   floor(m * n) = integer part of (mantissa * n) / 10^k
//
// Since m <= 10 and n <= 100, m*n <= 1000, so the integer part is tiny and
// fits comfortably in a long long.

#include <algorithm>
#include <iostream>
#include <string>

using namespace std;

// Multiply a non-negative decimal digit string (no sign, no decimal point) by
// a small non-negative integer n.  Returns the resulting digit string.
static string mulSmall(const string& digits, long long n) {
    string res;
    long long carry = 0;
    for (int i = (int)digits.size() - 1; i >= 0; --i) {
        long long prod = (digits[i] - '0') * n + carry;
        res.push_back(char('0' + prod % 10));
        carry = prod / 10;
    }
    while (carry > 0) {
        res.push_back(char('0' + carry % 10));
        carry /= 10;
    }
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    string ms;   // the real number m, read verbatim as a token
    long long n;
    if (!(cin >> ms >> n)) {
        return 0;
    }

    // Separate the integer and fractional parts of m.
    size_t dot = ms.find('.');
    string ip, frac;
    if (dot == string::npos) {
        ip = ms;
        frac.clear();
    } else {
        ip = ms.substr(0, dot);
        frac = ms.substr(dot + 1);
    }
    size_t k = frac.size();

    // mantissa = m's digits with the decimal point removed.
    string mantissa = ip + frac;

    // product = (mantissa * n) as a decimal string.
    string prod = mulSmall(mantissa, n);

    long long floorVal = 0;
    if (prod.size() > k) {
        string intPart = prod.substr(0, prod.size() - k);
        for (char c : intPart) {
            floorVal = floorVal * 10 + (c - '0');
        }
    }
    // Otherwise m*n < 1, so floor(m*n) == 0.

    cout << (floorVal % 2) << "\n";
    return 0;
}
