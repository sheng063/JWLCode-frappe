#include <iostream>

using namespace std;

int main() {
    // Statement declares two int variables a and b read from a single line
    // of input, with 0 < a < 100 and 0 < b < 100.
    long long a, b;
    cin >> a >> b;

    // Output a+b, a-b, a*b, a/b as integers, space-separated.
    // Integer division of positive operands truncates toward zero,
    // matching C++ semantics described in the statement.
    cout << (a + b) << " " << (a - b) << " " << (a * b) << " " << (a / b) << "\n";

    return 0;
}
