#include <iostream>

int main() {
    int y, m;
    std::cin >> y >> m;

    int days;
    if (m == 1 || m == 3 || m == 5 || m == 7 || m == 8 || m == 10 || m == 12) {
        days = 31;
    } else if (m == 4 || m == 6 || m == 9 || m == 11) {
        days = 30;
    } else { // m == 2
        bool leap = (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0);
        days = leap ? 29 : 28;
    }

    std::cout << days << "\n";
    return 0;
}
