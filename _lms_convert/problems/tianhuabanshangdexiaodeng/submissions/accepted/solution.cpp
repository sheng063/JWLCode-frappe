// 天花板上的小灯
// Input: two space-separated integers a, b (1 <= a,b <= 100000) = number of rows and columns.
// Output: a * b, the total number of lights.
#include <iostream>

int main() {
    long long a, b;
    if (!(std::cin >> a >> b)) {
        return 0;
    }
    std::cout << a * b << std::endl;
    return 0;
}
