#include <iostream>

int main() {
    long long a[5];
    for (int i = 0; i < 5; ++i) {
        std::cin >> a[i];
    }

    long long d = a[1] - a[0];
    bool ok = true;
    for (int i = 1; i + 1 < 5; ++i) {
        if (a[i + 1] - a[i] != d) {
            ok = false;
            break;
        }
    }

    std::cout << (ok ? "YES" : "NO") << "\n";
    return 0;
}
