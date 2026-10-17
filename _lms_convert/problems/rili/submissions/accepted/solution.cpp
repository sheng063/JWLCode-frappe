#include <iostream>

int main() {
    long long n = 0;
    if (!(std::cin >> n)) {
        return 0;
    }
    // Today (Nov 6) is Sunday = 0. n days later the weekday is (0 + n) mod 7,
    // which equals n % 7 in the range 0..6.
    std::cout << (n % 7) << "\n";
    return 0;
}
