#include <iostream>
#include <iomanip>

int main() {
    double chang, kuan;
    // Statement: input one line containing two floating-point numbers.
    if (!(std::cin >> chang >> kuan)) {
        return 0;
    }
    // Perimeter = 2 * (length + width), rounded to 3 decimal places.
    double perimeter = 2.0 * (chang + kuan);
    std::cout << std::fixed << std::setprecision(3) << perimeter << "\n";
    return 0;
}
