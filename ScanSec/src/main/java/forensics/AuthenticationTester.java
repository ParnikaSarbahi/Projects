package forensics;

import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Base64;
import java.util.Scanner;

public class AuthenticationTester implements ForensicAnalyzer {

    @Override
    public void analyze() {
        main(new String[0]);
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.println("\n⚠️  WARNING: Only use this on systems you own or have written permission to test.");
        System.out.print("Enter target URL (e.g., http://testphp.vulnweb.com/login.php): ");
        String target = scanner.nextLine().trim();

        if (!Validator.isValidURL(target)) {
            Logger.error("Invalid URL.");
            scanner.close();
            return;
        }

        Logger.info("Starting authentication test on: " + target);
        testDefaultCredentials(target);
        Logger.info("Authentication testing complete.");
        scanner.close();
    }

    private static void testDefaultCredentials(String target) {
        String[][] credentials = {
            {"admin",  "admin"},
            {"admin",  "password"},
            {"admin",  "123456"},
            {"admin",  ""},
            {"root",   "root"},
            {"root",   "toor"},
            {"root",   ""},
            {"user",   "user"},
            {"user",   "password"},
            {"test",   "test"},
            {"guest",  "guest"}
        };

        System.out.println("\n========== AUTHENTICATION TESTER ==========");
        System.out.println("Target  : " + target);
        System.out.println("Testing : " + credentials.length + " common credential pairs");
        System.out.println("-------------------------------------------");

        int successCount = 0;

        for (String[] pair : credentials) {
            String username = pair[0];
            String password = pair[1];

            int code = tryCredential(target, username, password);

            if (code == 200) {
                System.out.println("SUCCESS : " + username + " / " + password
                    + "  (HTTP " + code + ")");
                Logger.warn("Valid credentials found: " + username + ":" + password
                    + " on " + target);
                successCount++;
            } else if (code == 401) {
                System.out.println("FAILED  : " + username + " / "
                    + (password.isEmpty() ? "(empty)" : password)
                    + "  (HTTP 401 Unauthorized)");
            } else if (code == 403) {
                System.out.println("BLOCKED : " + username + " / " + password
                    + "  (HTTP 403 — account may be locked)");
            } else if (code == -1) {
                System.out.println("ERROR   : Could not connect for "
                    + username + " / " + password);
            } else {
                System.out.println("UNKNOWN : " + username + " / " + password
                    + "  (HTTP " + code + ")");
            }
        }

        System.out.println("-------------------------------------------");
        if (successCount > 0) {
            System.out.println("🚨 " + successCount + " valid credential(s) found!");
        } else {
            System.out.println("No default credentials worked on this target.");
        }
        System.out.println("===========================================\n");
    }

    private static int tryCredential(String target, String username, String password) {
        try {
            HttpURLConnection conn = (HttpURLConnection) new URL(target).openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(4000);
            conn.setReadTimeout(4000);

            String credentials = username + ":" + password;
            String encoded = Base64.getEncoder().encodeToString(credentials.getBytes());
            conn.setRequestProperty("Authorization", "Basic " + encoded);

            int code = conn.getResponseCode();
            conn.disconnect();
            return code;

        } catch (Exception e) {
            return -1;
        }
    }
}
