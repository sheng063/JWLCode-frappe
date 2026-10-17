#include <iostream>

int main() {
    long long tou, jiao;
    if (!(std::cin >> tou >> jiao)) {
        return 0;
    }

    // Let c = number of chickens, r = number of rabbits.
    //   c + r = tou
    //   2c + 4r = jiao
    // => r = (jiao - 2*tou) / 2,  c = tou - r
    // Use long long so that 2*tou and the intermediate arithmetic cannot
    // overflow int even when the input values are near the int range.
    long long rabbits = (jiao - 2 * tou) / 2;
    long long chickens = tou - rabbits;

    std::cout << rabbits << '\n' << chickens << '\n';
    return 0;
}
