#include <iostream>

int main() {
    double n;
    if (!(std::cin >> n)) {
        return 0;
    }

    // Inclusive condition: 1.2 <= n <= 1.5 -> half-price ticket (YES).
    // A tiny epsilon absorbs floating-point representation error so that an
    // exact input like "1.2" or "1.5" is still classified correctly.
    const double EPS = 1e-9;

    if (n >= 1.2 - EPS && n <= 1.5 + EPS) {
        std::cout << "YES\n";
    } else {
        std::cout << "NO\n";
    }

    return 0;
}
