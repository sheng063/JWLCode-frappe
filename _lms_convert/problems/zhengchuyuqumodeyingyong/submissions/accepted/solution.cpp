#include <iostream>

int main() {
    long long a, b;
    // a = number of 蒜头君 (Garlic), b = number of 花椰妹 (Broccoli).
    if (!(std::cin >> a >> b)) {
        return 0;
    }
    // Cross-compose two new two-digit numbers:
    //   tens digit  = own units digit
    //   units digit = the other's tens digit
    long long broc = (b % 10) * 10 + (a / 10);   // Broccoli's number
    long long garlic = (a % 10) * 10 + (b / 10); // Garlic's number
    std::cout << broc << "\n";
    std::cout << garlic << "\n";
    return 0;
}
