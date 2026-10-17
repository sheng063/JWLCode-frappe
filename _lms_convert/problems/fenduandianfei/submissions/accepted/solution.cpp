#include <iostream>

int main() {
    long long n;
    if (!(std::cin >> n)) {
        return 0;
    }
    long long fee;
    if (n <= 150) {
        fee = n;                       // parts at 1 yuan / kWh
    } else if (n <= 400) {
        fee = 150 + 2LL * (n - 150);   // first 150 at 1, rest at 2
    } else {
        fee = 650 + 3LL * (n - 400);   // first 150 at 1, next 250 at 2, rest at 3
    }
    std::cout << fee << "\n";
    return 0;
}
