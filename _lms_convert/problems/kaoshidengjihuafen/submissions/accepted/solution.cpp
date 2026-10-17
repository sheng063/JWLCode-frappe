// 考试等级划分 (Exam Grade Classification)
// Given a percentage score fen (0 <= fen <= 100), output its grade:
//   90 and above -> A
//   80 to 89     -> B
//   70 to 79     -> C
//   below 70     -> D
#include <iostream>
using namespace std;

int main() {
    long long fen;
    if (!(cin >> fen)) {
        return 0;
    }
    if (fen >= 90) {
        cout << "A" << endl;
    } else if (fen >= 80) {
        cout << "B" << endl;
    } else if (fen >= 70) {
        cout << "C" << endl;
    } else {
        cout << "D" << endl;
    }
    return 0;
}
