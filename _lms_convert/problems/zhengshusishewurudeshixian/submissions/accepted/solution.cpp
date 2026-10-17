// 正数四舍五入的实现 (rounding positive numbers)
// Round m and n to the nearest integer using 四舍五入 (half-up rounding).
//
// The statement gives no numeric bound for m and n (only "positive numbers"),
// so the values are handled as decimal digit strings to stay exact for any
// magnitude instead of relying on floating point precision.
//
// 四舍五入 on a positive decimal: drop the fractional part; if the first
// dropped digit is >= 5, round the integer part up by one, otherwise leave it.

#include <iostream>
#include <string>

using namespace std;

// Remove leading zeros but always keep at least one digit.
static string stripZeros(const string& s) {
    size_t p = s.find_first_not_of('0');
    if (p == string::npos) return "0";
    return s.substr(p);
}

// Add one to a non-negative decimal integer string (big-number increment).
static string addOne(const string& s) {
    string r = s;
    int i = static_cast<int>(r.size()) - 1;
    while (i >= 0 && r[i] == '9') {
        r[i] = '0';
        --i;
    }
    if (i < 0) return "1" + r;
    r[i] = static_cast<char>(r[i] + 1);
    return r;
}

// Round a positive decimal string ("digits" or "digits.digits") half-up to an
// integer, returned as a decimal digit string.
static string roundHalfUp(const string& x) {
    size_t dot = x.find('.');
    string ip = (dot == string::npos) ? x : x.substr(0, dot);
    string fp = (dot == string::npos) ? string() : x.substr(dot + 1);

    if (!fp.empty() && fp[0] >= '5') {
        ip = addOne(ip);
    }
    return stripZeros(ip);
}

int main() {
    string m, n;
    if (!(cin >> m >> n)) return 0;  // no input / malformed: print nothing

    cout << roundHalfUp(m) << '\n';
    cout << roundHalfUp(n) << '\n';
    return 0;
}
