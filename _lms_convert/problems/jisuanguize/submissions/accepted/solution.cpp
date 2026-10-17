#include <iostream>

int main() {
    long long x;
    // The statement guarantees exactly one integer x, 0 <= x < 100.
    if (!(std::cin >> x)) {
        return 0;
    }

    long long ans;
    if (x >= 0 && x < 5) {
        // 0 <= x < 5  ->  2 - x
        ans = 2 - x;
    } else if (x >= 5 && x < 10) {
        // 5 <= x < 10  ->  5 - 10 * (x - 3) * (x - 3)
        ans = 5 - 10LL * (x - 3) * (x - 3);
    } else {
        // 10 <= x < 100  ->  2 * x - 5
        ans = 2 * x - 5;
    }

    std::cout << ans << "\n";
    return 0;
}
