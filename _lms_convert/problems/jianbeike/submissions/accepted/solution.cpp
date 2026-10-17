#include <iostream>

int main() {
    // Read the weight a (jin) of each of the two shells already in the box.
    double a;
    std::cin >> a;

    // The box holds at most 20 jin; two shells each weigh a jin are already in it.
    double remaining = 20.0 - 2.0 * a;

    // Default (6 significant digit) general formatting reproduces the expected
    // answers: 16, 15, 4.4, 0, 13 for the sample/lms inputs.
    std::cout << remaining << "\n";
    return 0;
}
