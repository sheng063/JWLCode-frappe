#include <iostream>

using namespace std;

int main() {
    double n;
    if (!(cin >> n)) {
        return 0;
    }
    // Cast the real score to an integer, then integer-divide by 10.
    int t = static_cast<int>(n) / 10;
    char level;
    switch (t) {
        case 10: level = 'A'; break;
        case 9:  level = 'B'; break;
        case 8:  level = 'C'; break;
        case 7:  level = 'D'; break;
        case 6:  level = 'E'; break;
        default: level = 'F'; break;
    }
    cout << level << "\n";
    return 0;
}
