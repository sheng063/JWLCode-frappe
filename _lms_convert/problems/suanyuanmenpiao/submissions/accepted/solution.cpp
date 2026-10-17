#include <iostream>

int main() {
    long long n;
    if (!(std::cin >> n)) {
        return 0;
    }
    // Ticket price is 50 yuan each. Buying 30 or more at once means each
    // ticket costs 2 less (48 yuan each). Use long long since n * 48 can
    // exceed the int range.
    const long long price = (n >= 30) ? (50 - 2) : 50;
    std::cout << n * price << "\n";
    return 0;
}
