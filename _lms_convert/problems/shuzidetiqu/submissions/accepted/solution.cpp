#include <iostream>

int main() {
    long long n;
    char c;
    if (!(std::cin >> n)) {
        return 0;
    }
    if (!(std::cin >> c)) {
        return 0;
    }
    long long ans = (c == 'a') ? (n / 10) : (n % 10);
    std::cout << ans << std::endl;
    return 0;
}
