#include <iostream>
#include <iomanip>

int main() {
    int X;
    char Y;
    if (!(std::cin >> X >> Y)) {
        return 0;
    }

    double fee;
    if (X <= 10) {
        fee = 9.0 * X;
    } else {
        fee = 90.0 + 2.0 * (X - 10);
    }

    if (Y == 'A') {
        // A coupon deducts half of the shipping fee.
        fee = fee / 2.0;
    } else if (Y == 'B') {
        // B coupon deducts 7 yuan.
        fee = fee - 7.0;
    }

    // C coupon: no discount applied.

    std::cout << std::fixed << std::setprecision(1) << fee << std::endl;
    return 0;
}
