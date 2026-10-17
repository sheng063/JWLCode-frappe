#include <iostream>

using namespace std;

int main() {
    // n = 苹果总数 (>=1), x = 虫子吃掉一个苹果所需小时数 (>=1), y = 经过小时数 (>=0)
    long long n, x, y;
    if (!(cin >> n >> x >> y)) return 0;

    // 虫子在 y 小时内开始吃掉的苹果数（吃完或正在吃都算不完整）= ceil(y/x)
    long long eaten;
    if (y == 0) {
        eaten = 0;
    } else {
        eaten = y / x;
        if (y % x != 0) eaten += 1;  // 向上取整，避免 (y+x-1) 溢出
    }

    long long rem = n - eaten;
    if (rem < 0) rem = 0;  // 已吃完则剩余为 0

    cout << rem << "\n";
    return 0;
}
