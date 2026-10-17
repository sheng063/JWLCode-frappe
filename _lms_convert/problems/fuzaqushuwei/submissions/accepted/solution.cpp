#include <iostream>

int main() {
    long long n;
    if (!(std::cin >> n)) {
        return 0;
    }
    std::cout << (n / 100) << "\n";
    std::cout << ((n / 10) % 10) << "\n";
    std::cout << (n % 10) << "\n";
    return 0;
}
