#include <iostream>

int main() {
    // Input: two integers a and b, each within [-2^31, 2^31 - 1].
    // Read them as long long to be safe.
    long long a, b;
    if (!(std::cin >> a >> b)) {
        return 0;
    }

    // First line: 1 if a == b else 0.
    // Second line: 1 if a != b else 0 (the negation of the first).
    std::cout << (a == b ? 1 : 0) << "\n";
    std::cout << (a != b ? 1 : 0) << "\n";
    return 0;
}
