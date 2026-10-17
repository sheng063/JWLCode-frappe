#include <iostream>

int main() {
    long long X;
    if (!(std::cin >> X)) {
        return 0;
    }
    long long Y;
    if (X <= 15) {
        Y = 6 * X;
    } else {
        Y = 15 * 6 + (X - 15) * 9;
    }
    std::cout << Y << std::endl;
    return 0;
}
