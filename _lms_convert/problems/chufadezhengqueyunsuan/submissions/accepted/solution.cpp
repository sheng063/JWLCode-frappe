#include <iostream>
#include <climits>

int main() {
    long long a, b;
    if (!(std::cin >> a >> b)) {
        // No valid input; nothing to print.
        return 0;
    }

    if (b == 0) {
        std::cout << "ERROR" << std::endl;
        return 0;
    }

    // Guard the one case where signed division overflows: LLONG_MIN / -1.
    // Mathematical quotient is 2^63, which does not fit in a signed long long.
    if (a == LLONG_MIN && b == -1) {
        std::cout << "9223372036854775808" << std::endl;
        return 0;
    }

    std::cout << a / b << std::endl;
    return 0;
}
