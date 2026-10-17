#include <iostream>
#include <string>

int main() {
    std::string x;
    // The statement guarantees the input is exactly one of 'a', 'b', 'c'.
    if (std::cin >> x) {
        if (x == "a") {
            std::cout << "It is good\n";
        } else if (x == "b") {
            std::cout << "OMG\n";
        } else if (x == "c") {
            std::cout << "Yes!\n";
        }
    }
    return 0;
}
