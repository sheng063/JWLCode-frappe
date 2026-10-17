#include <iostream>

// 蒜头君买文具
//
// n people, each boy needs m pencils, each girl needs 2*m pencils, total k.
// Let g = number of girls, b = number of boys. Then b + g = n and
//   m*b + 2m*g = m*(b + 2g) = m*((n-g) + 2g) = m*(n + g) = k
//   => g = k/m - n
// The input guarantees k admits an integer (boys, girls) split, so k/m is exact.

int main() {
    long long n, m, k;
    std::cin >> n >> m >> k;
    // Read as long long for safety (ranges are small, but k/m is exact here).
    long long g = k / m - n;
    std::cout << g << "\n";
    return 0;
}
