#include <iostream>
#include <iomanip>
#include <string>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    std::string unit;
    double t;
    if (!(std::cin >> unit >> t)) {
        return 0;
    }

    std::cout << std::fixed;
    if (unit == "C") {
        // Celsius -> Fahrenheit: 1.8 * t + 32, keep 2 decimals
        double f = 1.8 * t + 32.0;
        std::cout << std::setprecision(2) << f << "\n";
    } else {
        // Fahrenheit -> Celsius: 5 * (t - 32) / 9, keep 5 decimals
        double c = 5.0 * (t - 32.0) / 9.0;
        std::cout << std::setprecision(5) << c << "\n";
    }

    return 0;
}
