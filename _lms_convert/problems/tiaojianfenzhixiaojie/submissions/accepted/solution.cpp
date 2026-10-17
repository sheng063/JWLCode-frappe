#include <iostream>

int main()
{
    long long a, b, c;
    std::cin >> a >> b >> c;

    if (a == b) {
        std::cout << 1 << '\n';
    } else if (b != c) {
        std::cout << 2 << '\n';
    } else {
        std::cout << 3 << '\n';
    }

    return 0;
}
