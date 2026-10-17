#include <iostream>

int main() {
    long long year;
    std::cin >> year;

    bool leap = false;
    if (year % 400 == 0) {
        leap = true;
    } else if (year % 100 == 0) {
        leap = false;
    } else if (year % 4 == 0) {
        leap = true;
    }

    std::cout << (leap ? 29 : 28) << std::endl;
    return 0;
}
