#include <iostream>

using namespace std;

int main() {
    long long n, x;
    // n: 蒜头君's age, x: how many years older than 蒜头君 10 years ago.
    // 花椰妹's age = (n - 10) + x.
    if (!(cin >> n >> x)) {
        return 0;
    }
    cout << (n - 10) + x << "\n";
    return 0;
}
