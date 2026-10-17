#include <iostream>

int main() {
    long long a, b, x, y;
    if (!(std::cin >> a >> b >> x >> y)) {
        return 0;
    }

    bool ab = (a > b);   // result of a > b
    bool xy = (x < y);   // result of x < y

    // Line 1: (a>b), (x<y), ((a>b) AND (x<y))
    std::cout << (ab ? 1 : 0) << ' '
              << (xy ? 1 : 0) << ' '
              << ((ab && xy) ? 1 : 0) << "\n";

    // Line 2: (a>b), (x<y), ((a>b) OR (x<y))
    std::cout << (ab ? 1 : 0) << ' '
              << (xy ? 1 : 0) << ' '
              << ((ab || xy) ? 1 : 0) << "\n";

    // Line 3: !(a>b), !(x<y)
    std::cout << (!ab ? 1 : 0) << ' ' << (!xy ? 1 : 0) << "\n";

    return 0;
}
