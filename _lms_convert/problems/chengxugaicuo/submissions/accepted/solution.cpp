#include <iostream>

int main() {
    long long a, b, c;
    std::cin >> a >> b >> c;
    // a, b, c <= 10000, so the product can reach 10^12,
    // which overflows int; use long long.
    std::cout << a * b * c << std::endl;
    return 0;
}
