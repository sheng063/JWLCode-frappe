// 求面积的问题 (Calculate the area)
//
// Input:
//   line 1: a single character 'r' (rectangle) or 't' (triangle)
//   line 2: two real numbers m and n
// For a rectangle, m and n are the length and width; the area is m*n.
// For a triangle, m and n are the base and height; the area is m*n/2.
//
// Output:
//   a single line with the area of the shape.
#include <iomanip>
#include <iostream>

int main() {
    char kind = 0;
    double m = 0.0, n = 0.0;

    // Read the shape character and the two side lengths.
    if (!(std::cin >> kind)) {
        return 0;
    }
    std::cin >> m >> n;

    double area = 0.0;
    if (kind == 'r') {
        area = m * n;
    } else { // kind == 't'
        area = m * n / 2.0;
    }

    std::cout << std::setprecision(15) << area << "\n";
    return 0;
}
