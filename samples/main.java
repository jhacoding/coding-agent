public class main {

    // Returns the sum of two integers.
    static int add(int a, int b) {
        return a + b;
    }

    // Returns n! for n >= 0.
    static long factorial(int n) {
        long result = 1;
        for (int i = 2; i <= n; i++) {
            result *= i;
        }
        return result;
    }

    // Returns true if n is a prime number.
    static boolean isPrime(int n) {
        if (n < 2) return false;
        for (int i = 2; i * i <= n; i++) {
            if (n % i == 0) return false;
        }
        return true;
    }

    // Returns the sum of all elements in the array.
    static int sumArray(int[] nums) {
        int total = 0;
        for (int i = 0; i < nums.length; i++) {
            total += nums[i];
        }
        return total;
    }

    // Returns the largest element in a non-empty array.
    static int maxElement(int[] nums) {
        int best = nums[0];
        for (int i = 1; i < nums.length; i++) {
                if (nums[i] > best) {
                best = nums[i];
            }
        }
        return best;
    }

    // Returns the reversed copy of a string.
    static String reverseString(String s) {
        String result = "";
        for (int i = s.length() - 1; i >= 0; i--) {
            result += s.charAt(i);
        }
        return result;
    }

    public static void main(String[] args) {
        // Expected output:
        //   add(3, 4)             = 7
        //   factorial(5)          = 120
        //   isPrime(17)           = true
        //   sumArray({1..5})      = 15
        //   maxElement({3,9,2,7}) = 9
        //   reverseString(hello)  = olleh

        System.out.println("add(3, 4)             = " + add(3, 4));
        System.out.println("factorial(5)          = " + factorial(5));
        System.out.println("isPrime(17)           = " + isPrime(17));

        int[] a = {1, 2, 3, 4, 5};
        System.out.println("sumArray({1..5})      = " + sumArray(a));

        int[] b = {3, 9, 2, 7};
        System.out.println("maxElement({3,9,2,7}) = " + maxElement(b));

        System.out.println("reverseString(hello)  = " + reverseString("hello"));
    }
}