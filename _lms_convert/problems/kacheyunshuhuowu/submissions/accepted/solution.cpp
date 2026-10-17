#include <iostream>

int main() {
    long long m;
    if (!(std::cin >> m)) {
        return 0;
    }

    // Red truck carries up to 5 toys per trip, blue carries up to 2.
    long long red = (m + 4) / 5;   // ceil(m / 5)
    long long blue = (m + 1) / 2;  // ceil(m / 2)

    // Only one truck may be chosen; pick the one needing fewer trips.
    long long ans = red < blue ? red : blue;
    std::cout << ans << std::endl;

    return 0;
}
