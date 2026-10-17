#include <iostream>

int main() {
    // Read the relative air humidity H.
    long long H = 0;
    if (!(std::cin >> H)) {
        // No input; nothing sensible to do. Print NO by convention.
        std::cout << "NO\n";
        return 0;
    }
    // It is about to rain when the humidity is greater than 55.
    if (H > 55) {
        std::cout << "YES\n";
    } else {
        std::cout << "NO\n";
    }
    return 0;
}
