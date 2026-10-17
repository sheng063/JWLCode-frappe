#include <iostream>

int main() {
    // Two different floating-point numbers a, b are given; output a / b.
    double a, b;
    if (!(std::cin >> a >> b)) {
        return 0;
    }
    std::cout << (a / b) << "\n";
    return 0;
}
