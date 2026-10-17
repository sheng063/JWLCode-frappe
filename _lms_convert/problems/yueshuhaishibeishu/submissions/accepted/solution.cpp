#include <iostream>

// 约数还是倍数
// Input: a single line with two space-separated integers a, b.
//        They satisfy a divisor-multiple relationship and are within int range.
// Output: if a > b print "a / b = <a/b>", else print "b / a = <b/a>".

int main() {
    long long a, b;
    if (!(std::cin >> a >> b)) {
        return 0;
    }
    if (a > b) {
        std::cout << "a / b = " << (a / b) << "\n";
    } else {
        std::cout << "b / a = " << (b / a) << "\n";
    }
    return 0;
}
