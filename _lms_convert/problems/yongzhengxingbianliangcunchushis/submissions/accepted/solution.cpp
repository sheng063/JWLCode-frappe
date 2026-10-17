#include <iostream>

int main() {
    // Read the real number m into a double variable.
    double m;
    std::cin >> m;

    // Store its (truncated toward zero) integer value into an int variable.
    int n = static_cast<int>(m);

    // Output the double value, then the int value.
    std::cout << m << "\n" << n << "\n";
    return 0;
}
