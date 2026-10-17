#include <iostream>

using namespace std;

int main() {
    int x;
    if (!(cin >> x)) return 0;

    // x is a three-digit number, 100 <= x <= 999.
    int first = x / 100;   // hundreds digit (首位)
    int last  = x % 10;    // units digit   (末位)

    if (first * last < first + last)
        cout << "YES\n";
    else
        cout << "NO\n";

    return 0;
}
