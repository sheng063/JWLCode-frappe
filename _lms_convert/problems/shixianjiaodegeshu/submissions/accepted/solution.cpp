#include <iostream>

int main() {
    long long n;
    std::cin >> n;
    // Cut off one corner: it removes 1 corner and creates 2 new ones,
    // so each cut increases the corner count by 1. Starting from 4,
    // after n cuts the shape has 4 + n corners.
    std::cout << (n + 4) << "\n";
    return 0;
}
