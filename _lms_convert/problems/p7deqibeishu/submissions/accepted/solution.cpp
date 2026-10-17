#include <iostream>

int main() {
    long long n;
    if (!(std::cin >> n)) {
        return 0;
    }
    if (n % 7 == 0 && n % 2 != 0) {
        std::cout << "YES\n";
    } else {
        std::cout << "NO\n";
    }
    return 0;
}
