#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    long long a, b, c;
    if (!(std::cin >> a >> b >> c)) {
        return 0;
    }
    std::vector<long long> v = {a, b, c};
    std::sort(v.begin(), v.end());
    std::cout << v[0] << ' ' << v[1] << ' ' << v[2] << '\n';
    return 0;
}
