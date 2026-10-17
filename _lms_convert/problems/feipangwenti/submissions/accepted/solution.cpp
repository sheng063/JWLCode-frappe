#include <iostream>

int main() {
    long long m, h;
    if (!(std::cin >> m >> h)) {
        return 0;
    }
    // x = floor(100000 * m / (h * h)); all terms positive so integer division = integer part.
    long long x = (100000LL * m) / (h * h);
    if (x < 180) {
        std::cout << "Underweight\n";
    } else if (x < 240) {
        std::cout << "Normal\n";
    } else {
        std::cout << "Overweight\n";
    }
    return 0;
}
