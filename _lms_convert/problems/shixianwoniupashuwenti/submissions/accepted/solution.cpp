#include <iostream>

int main() {
    long long n, a, b;
    if (!(std::cin >> n >> a >> b)) {
        return 0;
    }
    // The snail reaches the top on day k when the cumulative daytime position
    // k*a - (k-1)*b = k*(a-b) + b is at least n.  Given a > b and n-a is a
    // multiple of (a-b), the smallest such k is 1 + (n-a)/(a-b); it can never
    // be less than 1.
    long long days = 1 + (n - a) / (a - b);
    if (days < 1) {
        days = 1;
    }
    std::cout << days << "\n";
    return 0;
}
