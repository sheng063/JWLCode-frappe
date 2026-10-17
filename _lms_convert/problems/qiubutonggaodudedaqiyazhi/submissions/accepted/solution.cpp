#include <iostream>
#include <string>
using namespace std;

typedef __int128 int128;

// Print an int128 to stdout as a decimal integer.
void print_int128(int128 v) {
    if (v == 0) {
        cout << '0';
        return;
    }
    if (v < 0) {
        cout << '-';
        v = -v;
    }
    string s;
    while (v > 0) {
        s.push_back(char('0' + (int)(v % 10)));
        v /= 10;
    }
    for (int i = (int)s.size() - 1; i >= 0; --i) cout << s[i];
}

int main() {
    string s;
    if (!(cin >> s)) return 0;
    cin.ignore(10000, '\n');

    size_t i = 0;
    bool neg = false;
    if (i < s.size() && (s[i] == '+' || s[i] == '-')) {
        neg = (s[i] == '-');
        ++i;
    }

    string intPart, fracPart;
    while (i < s.size() && isdigit((unsigned char)s[i])) intPart.push_back(s[i++]);
    if (i < s.size() && s[i] == '.') {
        ++i;
        while (i < s.size() && isdigit((unsigned char)s[i])) fracPart.push_back(s[i++]);
    }

    // h = sign * (intPart . fracPart)
    int128 hScale = 0;              // h * 10^k
    for (char c : intPart) hScale = hScale * 10 + (c - '0');
    for (char c : fracPart) hScale = hScale * 10 + (c - '0');
    if (neg) hScale = -hScale;

    int k = (int)fracPart.size();   // number of fraction digits
    int128 D = 1;
    for (int j = 0; j < k; ++j) D *= 10;

    // answer = 100000 - 10*h = (100000*10^k - 10*hScale) / 10^k
    int128 num = (int128)100000 * D - (int128)10 * hScale;

    int128 q = num / D;
    int128 r = num % D;
    if (r < 0) { r += D; q -= 1; }

    print_int128(q);
    if (r != 0) {
        cout << '.';
        // fraction = r zero-padded to k digits, then trim trailing zeros
        string fpart = to_string((long long)r);
        while ((int)fpart.size() < k) fpart = "0" + fpart;
        while (fpart.size() > 0 && fpart.back() == '0') fpart.pop_back();
        cout << fpart;
    }
    cout << '\n';
    return 0;
}
