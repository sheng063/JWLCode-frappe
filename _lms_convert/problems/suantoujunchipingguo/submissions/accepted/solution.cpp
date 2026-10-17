#include <iostream>
#include <string>

using namespace std;
using i128 = __int128_t;

int main() {
    // m: apples per minute (decimal), n: minutes (integer).
    // Complete apples = floor(m * n). Compute exactly with decimal
    // arithmetic to avoid floating-point precision issues:
    //   m = I + F / 10^d   =>   m*n = I*n + (F*n)/10^d
    // We take floor of the whole expression.
    string m;
    long long n;
    if (!(cin >> m)) return 0;
    if (!(cin >> n)) return 0;

    size_t dot = m.find('.');
    size_t ipEnd = (dot == string::npos) ? m.size() : dot;

    long long I = 0;                 // integer part
    for (size_t i = 0; i < ipEnd; ++i) {
        I = I * 10 + (m[i] - '0');
    }

    i128 F = 0, denom = 1;           // fractional part as integer / 10^d
    if (dot != string::npos) {
        for (size_t i = dot + 1; i < m.size(); ++i) {
            F = F * 10 + (m[i] - '0');
            denom *= 10;
        }
    }

    // m >= 0 per constraints, so integer division truncates == floor.
    i128 total = (i128)I * n + (F * n) / denom;
    cout << (long long)total << "\n";
    return 0;
}
