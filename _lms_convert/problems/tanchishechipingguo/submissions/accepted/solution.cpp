#include <iostream>

int main() {
    // n: total apples, x: seconds to eat one apple, y: elapsed seconds.
    // The teacher guarantees 0 <= y <= n*x, so the snake never runs out of
    // apples within the elapsed time.
    long long n, x, y;
    if (!(std::cin >> n >> x >> y)) {
        return 0;  // no input: nothing to do
    }

    // If x == 0 the snake "takes no time" per apple; the guarantee forces y == 0,
    // so no apple has been touched and all n apples remain whole.
    if (x == 0) {
        std::cout << n << "\n";
        return 0;
    }

    // Number of apples the snake has begun eating after y seconds =
    // number fully eaten (floor(y/x)) plus the partial one in progress.
    // For a multiple of x exactly, that equals y/x; otherwise floor(y/x)+1.
    // Both cases equal ceil(y/x).
    long long started = (y + x - 1) / x;  // ceil(y/x)

    // Remainder stays >= 0 because of the guarantee y <= n*x.
    long long remaining = n - started;
    if (remaining < 0) {
        remaining = 0;
    }
    std::cout << remaining << "\n";
    return 0;
}
