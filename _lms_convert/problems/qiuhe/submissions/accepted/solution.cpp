#include <iostream>

int main() {
    long long n;
    std::cin >> n;
    long long ans = n * (n + 1) / 2;
    std::cout << ans << std::endl;
    return 0;
}
