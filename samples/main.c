#include <stdio.h>
#include <string.h>

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

// Returns 1 if n is a prime number, otherwise 0.
int isPrime(int n) {
    if (n < 2) return 0;
    for (int i = 2; i * i <= n; i++) {
        if (n % i == 0) return 0;
    }
    return 1;
}

// Returns the sum of all elements in the array.
int sumArray(const int arr[], int size) {
    int total = 0;
    for (int i = 0; i < size; i++) {
        total += arr[i];
    }
    return total;
}

// Returns the largest element in a non-empty array.
int maxElement(const int arr[], int size) {
    int best = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] > best) {
            best = arr[i];
        }
    }
    return best;
}

// Reverses a string in place.
void reverseString(char s[]) {
    int len = (int)strlen(s);
    for (int i = 0; i < len / 2; i++) {
        char tmp = s[i];
        s[i] = s[len - 1 - i];
        s[len - 1 - i] = tmp;
    }
}

int main() {
    // Expected output:
    //   add(3, 4)             = 7
    //   factorial(5)          = 120
    //   isPrime(17)           = true
    //   sumArray({1..5})      = 15
    //   maxElement({3,9,2,7}) = 9
    //   reverseString(hello)  = olleh

    printf("add(3, 4)             = %d\n", add(3, 4));
    printf("factorial(5)          = %lld\n", factorial(5));
    printf("isPrime(17)           = %s\n", isPrime(17) ? "true" : "false");

    int a[] = {1, 2, 3, 4, 5};
    printf("sumArray({1..5})      = %d\n", sumArray(a, 5));

    int b[] = {3, 9, 2, 7};
    printf("maxElement({3,9,2,7}) = %d\n", maxElement(b, 4));

    char word[] = "hello";
    reverseString(word);
    printf("reverseString(hello)  = %s\n", word);

    return 0;
}