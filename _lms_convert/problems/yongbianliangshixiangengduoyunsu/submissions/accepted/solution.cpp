#include <iostream>

int main() {
    // 正方形的边长固定为 2.5，使用变量存储边长。
    double side = 2.5;
    double perimeter = side * 4;      // 周长 = 边长 x 4
    double area = side * side;        // 面积 = 边长 x 边长

    std::cout << perimeter << std::endl;
    std::cout << area << std::endl;
    return 0;
}
