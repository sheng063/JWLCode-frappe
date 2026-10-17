#include <iostream>

int main() {
    long long x;
    if (!(std::cin >> x)) {
        return 0;
    }

    // Weights over 30 kg cannot be mailed.
    if (x > 30) {
        std::cout << "Fail\n";
        return 0;
    }

    // Progressive handling fee: a package costs a 2 yuan handling fee plus
    // the weight-portion charges listed in the table.
    //   x <= 10        : 1 yuan/kg
    //   10 < x <= 20   : 2 yuan/kg (for the portion above 10 kg)
    //   20 < x <= 30   : 3 yuan/kg (for the portion above 20 kg)
    long long fee = 2;                 // handling fee
    if (x <= 10) {
        fee += x * 1;
    } else if (x <= 20) {
        fee += 10 * 1 + (x - 10) * 2;
    } else {                            // 20 < x <= 30
        fee += 10 * 1 + 10 * 2 + (x - 20) * 3;
    }

    std::cout << fee << "\n";
    return 0;
}
