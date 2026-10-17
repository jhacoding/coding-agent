def add(a, b):
    """Returns the sum of two numbers."""
    return a + b


def factorial(n):
    """Returns n! for n >= 0."""
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def is_prime(n):
    """Returns True if n is a prime number."""
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def sum_list(nums):
    """Returns the sum of all elements in the list."""
    total = 0
    for x in nums:
        total += x
    return total


def max_element(nums):
    """Returns the largest element in a non-empty list."""
    best = nums[0]
    for x in nums[1:]:
        if x > best:
            best = x
    return best


def reverse_string(s):
    """Returns the reversed copy of a string."""
    result = ""
    for ch in s:
        result = ch + result
    return result


def main():
    # Expected output:
    #   add(3, 4)             = 7
    #   factorial(5)          = 120
    #   is_prime(17)          = True
    #   sum_list([1..5])      = 15
    #   max_element([3,9,2,7]) = 9
    #   reverse_string(hello) = olleh

    print("add(3, 4)             =", add(3, 4))
    print("factorial(5)          =", factorial(5))
    print("is_prime(17)          =", is_prime(17))
    print("sum_list([1..5])      =", sum_list([1, 2, 3, 4, 5]))
    print("max_element([3,9,2,7]) =", max_element([3, 9, 2, 7]))
    print("reverse_string(hello) =", reverse_string("hello"))


if __name__ == "__main__":
    main()