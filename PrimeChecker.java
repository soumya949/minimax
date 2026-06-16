public class PrimeChecker {
    
    // Prime function - checks if a number is prime
    public static boolean isPrime(int n) {
        // Numbers less than 2 are not prime
        if (n < 2) {
            return false;
        }
        
        // 2 is the only even prime
        if (n == 2) {
            return true;
        }
        
        // Even numbers are not prime
        if (n % 2 == 0) {
            return false;
        }
        
        // Check odd divisors up to square root of n
        for (int i = 3; i * i <= n; i += 2) {
            if (n % i == 0) {
                return false;
            }
        }
        
        return true;
    }
    
    // Main method to test the function
    public static void main(String[] args) {
        // Test some numbers
        int[] testNumbers = {1, 2, 3, 4, 5, 17, 18, 19, 100, 101};
        
        System.out.println("Prime Number Test:");
        System.out.println("------------------");
        
        for (int num : testNumbers) {
            System.out.println(num + " is prime: " + isPrime(num));
        }
    }
}