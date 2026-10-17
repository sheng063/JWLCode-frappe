#include <iostream>

int main() {
    char c;
    if (!(std::cin >> c)) {
        return 0;
    }
    if (c >= 'a' && c <= 'z') {
        // Lowercase letter -> uppercase.
        std::cout << static_cast<char>(c - 'a' + 'A') << '\n';
    } else if (c >= 'A' && c <= 'Z') {
        // Uppercase letter -> lowercase.
        std::cout << static_cast<char>(c - 'A' + 'a') << '\n';
    }
    return 0;
}
