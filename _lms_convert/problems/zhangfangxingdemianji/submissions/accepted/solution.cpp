#include <cstdio>
#include <iostream>

int main() {
    double l, w;
    // Read the two floating-point numbers (length and width).
    if (!(std::cin >> l >> w)) {
        return 0;
    }
    // Area of a rectangle: S = l * w, printed rounded to 3 decimal places.
    double area = l * w;
    std::printf("%.3f\n", area);
    return 0;
}
