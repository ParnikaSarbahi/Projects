package forensics;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.Map;

public class LogAnalyzer implements ForensicAnalyzer {

    private static final int BRUTE_FORCE_THRESHOLD = 3;

    @Override
    public void analyze() {
        Logger.info("Starting log analysis...");

        try (InputStream is = getClass().getClassLoader().getResourceAsStream("sample_auth.log")) {
            if (is == null) {
                Logger.error("sample_auth.log not found in resources!");
                return;
            }

            BufferedReader reader = new BufferedReader(new InputStreamReader(is));
            String line;
            int failedCount = 0;
            int successCount = 0;

            Map<String, Integer> failuresByIP = new HashMap<>();

            while ((line = reader.readLine()) != null) {
                if (line.contains("Failed password")) {
                    failedCount++;
                    Logger.warn("Suspicious entry: " + line);

                    String ip = extractIP(line);
                    if (ip != null) {
                        failuresByIP.put(ip, failuresByIP.getOrDefault(ip, 0) + 1);
                    }

                } else if (line.contains("Accepted password")) {
                    successCount++;
                    Logger.info("Successful login: " + line);
                }
            }

            System.out.println("\n========== LOG ANALYSIS SUMMARY ==========");
            System.out.println("Total failed login attempts : " + failedCount);
            System.out.println("Total successful logins     : " + successCount);

            System.out.println("\n--- Potential Brute Force Attackers ---");
            boolean found = false;
            for (Map.Entry<String, Integer> entry : failuresByIP.entrySet()) {
                if (entry.getValue() >= BRUTE_FORCE_THRESHOLD) {
                    System.out.println("IP: " + entry.getKey() + " -> " + entry.getValue() + " failed attempts (ALERT!)");
                    found = true;
                }
            }
            if (!found) {
                System.out.println("No brute force patterns detected.");
            }
            System.out.println("===========================================\n");

            Logger.info("Log analysis complete.");

        } catch (Exception e) {
            Logger.error("Error reading log file: " + e.getMessage());
        }
    }

    private String extractIP(String line) {
        String[] words = line.split(" ");
        for (int i = 0; i < words.length; i++) {
            if (words[i].equals("from") && i + 1 < words.length) {
                String candidate = words[i + 1];
                if (Validator.isValidIP(candidate)) {
                    return candidate;
                }
            }
        }
        return null;
    }
}
