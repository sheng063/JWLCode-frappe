#include <iostream>

int main() {
    long long a, b;
    char op;
    // Input consists of exactly three whitespace-separated parts: a, op, b.
    if (!(std::cin >> a >> op >> b)) {
        return 0;
    }

    long long result = 0;
    switch (op) {
        case '+':
            result = a + b;
            break;
        case '-':
            result = a - b;
            break;
        case '*':
            result = a * b;
            break;
        case '/':
            // Integer division (truncates toward zero). Division by zero is
            // never a valid input, but guard against it defensively.
            result = (b == 0) ? 0 : a / b;
            break;
        case '%':
            // Remainder has the sign of the dividend, matching C++ semantics.
            result = (b == 0) ? 0 : a % b;
            break;
        default:
            result = 0;
            break;
    }

    std::cout << result << "\n";
    return 0;
}
