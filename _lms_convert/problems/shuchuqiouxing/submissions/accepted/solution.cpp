#include <iostream>

int main() {
    long long shu;
    if (!(std::cin >> shu)) {
        return 0;
    }
    if (shu % 2 == 0) {
        std::cout << "oushu\n";
    } else {
        std::cout << "jishu\n";
    }
    return 0;
}
