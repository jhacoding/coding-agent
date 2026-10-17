#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

// Returns the sum of two integers.
int add(int a, int b) {
    return a + b;
}

// Returns n! for n >= 0.
long long factorial(int n) {
    long long result = 1;
    for (int i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

// Returns true if n is a prime number.
bool isPrime(int n) {
    if (n < 2) return false;
    for (int i = 2; i * i <= n; i++) {
        if (n % i == 0) return false;
    }
    return true;
}

// Returns the sum of all elements in the vector.
int sumVector(const vector<int>& nums) {
    int total = 0;
    for (size_t i = 0; i < nums.size(); i++) {
        total += nums[i];
    }
    return total;
}

// Returns the largest element in a non-empty vector.
int maxElement(const vector<int>& nums) {
    int best = nums[0];
    for (size_t i = 1; i < nums.size(); i++) {
        if (nums[i] > best) {
            best = nums[i];
        }
    }
    return best;
}

// Returns the reversed copy of a string.
string reverseString(const string& s) {
    string r = s;
    reverse(r.begin(), r.end());
    return r;
}

int main() {
    // Expected output:
    //   add(3, 4)            = 7
    //   factorial(5)         = 120
    //   isPrime(17)          = true
    //   sumVector({1..5})    = 15
    //   maxElement({3,9,2,7}) = 9
    //   reverseString(hello) = olleh

    cout << boolalpha;

    cout << "add(3, 4)            = " << add(3, 4) << endl;
    cout << "factorial(5)         = " << factorial(5) << endl;
    cout << "isPrime(17)          = " << isPrime(17) << endl;

    vector<int> a = {1, 2, 3, 4, 5};
    cout << "sumVector({1..5})    = " << sumVector(a) << endl;

    vector<int> b = {3, 9, 2, 7};
    cout << "maxElement({3,9,2,7}) = " << maxElement(b) << endl;

    cout << "reverseString(hello) = " << reverseString("hello") << endl;

    return 0;
}