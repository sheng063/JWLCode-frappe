#include <iostream>

int main() {
    // Statement: input two integers a, b with 0 < b < a < 1000.
    // Output YES iff a is an integer multiple of b (a % b == 0), else NO.
    long long a, b;
    if (!(std::cin >> a >> b)) {
        return 0;
    }
    if (a % b == 0) {
        std::cout << "YES\n";
    } else {
        std::cout << "NO\n";
    }
    return 0;
}
