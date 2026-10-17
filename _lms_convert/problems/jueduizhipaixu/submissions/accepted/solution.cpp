#include <iostream>
#include <algorithm>

int main() {
    // Read exactly the two integers described by the statement.
    long long a[2];
    std::cin >> a[0] >> a[1];

    // Sort by absolute value ascending; on equal absolute values, sort by the
    // numeric value ascending. The absolute values are computed on long long so
    // that abs(INT_MIN) does not overflow.
    std::sort(a, a + 2, [](long long x, long long y) {
        long long ax = x < 0 ? -x : x;
        long long ay = y < 0 ? -y : y;
        if (ax != ay) return ax < ay;
        return x < y;
    });

    std::cout << a[0] << " " << a[1] << "\n";
    return 0;
}
