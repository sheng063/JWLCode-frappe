#include <iostream>

int main() {
    int h;
    std::cin >> h;
    int x1, x2, x3;
    std::cin >> x1 >> x2 >> x3;

    // Standing on the 30-high stool, the lowest gift he can reach is h + 30.
    int reach = h + 30;

    int count = 0;
    if (x1 <= reach) ++count;
    if (x2 <= reach) ++count;
    if (x3 <= reach) ++count;

    std::cout << count << std::endl;
    return 0;
}
