#include <iostream>

int main() {
    // Distance d (meters) is a single integer on stdin.
    long long d;
    if (!(std::cin >> d)) {
        return 0;
    }

    // Walking takes d seconds (1 m/s).
    // Biking takes 27 + 23 + d/3 = 50 + d/3 seconds (3 m/s, plus setup overhead).
    // Compare d vs 50 + d/3  <=>  multiply by 3: 3d vs 150 + d  <=>  2d vs 150  <=>  d vs 75.
    // This comparison is exact for every integer d (no integer-division rounding).
    if (d < 75) {
        std::cout << "Walk\n";
    } else if (d == 75) {
        std::cout << "All\n";
    } else {
        std::cout << "Bike\n";
    }

    return 0;
}
