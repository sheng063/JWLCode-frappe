#include <iostream>

// 问题：输入一个整数 n，输出它的绝对值。
// 约束：-100 <= n <= 100。使用 long long 以防极限值下取负溢出。
int main() {
    long long n;
    if (std::cin >> n) {
        if (n < 0) {
            n = -n;
        }
        std::cout << n << "\n";
    }
    return 0;
}
