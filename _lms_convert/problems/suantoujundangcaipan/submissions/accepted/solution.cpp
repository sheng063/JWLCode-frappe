#include <iostream>

int main() {
    int n;
    if (!(std::cin >> n)) {
        return 0;
    }
    // n is a two-digit integer, 10 <= n <= 99.
    // Win iff the tens digit equals the units digit (e.g. 55 -> win).
    int tens = n / 10;
    int units = n % 10;
    if (tens == units) {
        std::cout << "win" << std::endl;
    } else {
        std::cout << "lose" << std::endl;
    }
    return 0;
}
