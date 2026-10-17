#include <iostream>
#include <iomanip>

int main() {
    long long n, m;
    if (!(std::cin >> n >> m)) {
        return 0;
    }
    // Total students = n + m. New students make up n / (n + m) of the school.
    // n >= 0 and m >= 10000, so the denominator is never zero.
    long long total = n + m;
    double ans = (double)n / (double)total;
    std::cout << std::setprecision(15) << ans << "\n";
    return 0;
}
