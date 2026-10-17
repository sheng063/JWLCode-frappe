#include <iostream>
#include <string>

int main() {
    std::string n;
    std::cin >> n;

    bool hasEven = false;
    for (char c : n) {
        int digit = c - '0';
        if (digit % 2 == 0) {
            hasEven = true;
            break;
        }
    }

    std::cout << (hasEven ? "YES" : "NO") << std::endl;
    return 0;
}
