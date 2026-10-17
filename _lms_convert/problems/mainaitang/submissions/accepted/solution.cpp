#include <iostream>
#include <cmath>

int main() {
    long long n;
    long double m;

    // n: number of candies bought for m yuan; m: price paid (float).
    // Unit price = m / n.  With 20 yuan => 20 / (m/n) = 20*n/m, floored.
    if (!(std::cin >> n >> m)) {
        return 0;
    }

    long long ans = static_cast<long long>(
        std::floor(20.0L * static_cast<long double>(n) / m));
    std::cout << ans << '\n';
    return 0;
}
