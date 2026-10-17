#include <iostream>
#include <cstdio>
#include <algorithm>
using namespace std;

int main() {
    long long m, p1, n, p2;
    if (!(cin >> m >> p1 >> n >> p2)) {
        return 0;
    }
    long long cm = m * p1;   // cost of strawberries
    long long cn = n * p2;   // cost of mangoes
    long long base = cm + cn;

    long long cents;         // price expressed in units of 0.01
    if (m + n >= 20) {
        // Discount applies: pick the fruit with the larger cost.
        long long mx = max(cm, cn);
        // final = base - 0.2*mx  =>  in hundredths: base*100 - mx*20
        cents = base * 100 - mx * 20;
    } else {
        cents = base * 100;
    }

    printf("%lld.%02lld\n", cents / 100, cents % 100);
    return 0;
}
