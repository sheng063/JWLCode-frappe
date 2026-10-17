#include <cstdio>

int main() {
    double shu;
    // Read the single floating-point number exactly as the statement specifies.
    if (scanf("%lf", &shu) != 1) {
        return 0;
    }
    // Output the value rounded to exactly 3 decimal places.
    printf("%.3f\n", shu);
    return 0;
}
