#include <iostream>

int main() {
    int yue, runnian;
    if (!(std::cin >> yue >> runnian)) {
        return 0;
    }

    int days;
    if (yue == 2) {
        // February: 29 days in a leap year, 28 in a common year.
        days = (runnian == 1) ? 29 : 28;
    } else if (yue == 4 || yue == 6 || yue == 9 || yue == 11) {
        days = 30;
    } else {
        days = 31;
    }

    std::cout << days << "\n";
    return 0;
}
