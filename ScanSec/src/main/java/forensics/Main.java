package forensics;

import java.util.Scanner;

public class Main {

    public static void main(String[] args) {
        // Load config and connect to DB at startup
        Config.load();
        Database.connect();

        Scanner scanner = new Scanner(System.in);
        boolean running = true;

        System.out.println("\n╔══════════════════════════════════════╗");
        System.out.println("║         ScanSec v2.0.0               ║");
        System.out.println("║   Network Security & Forensics Tool  ║");
        System.out.println("╚══════════════════════════════════════╝");

        while (running) {
            printMenu();
            System.out.print("Enter choice: ");

            String input = scanner.nextLine().trim();
            int choice;

            try {
                choice = Integer.parseInt(input);
            } catch (NumberFormatException e) {
                System.out.println("Please enter a number.");
                continue;
            }

            long startTime = System.currentTimeMillis();

            switch (choice) {
                case 1 -> {
                    ForensicAnalyzer analyzer = new LogAnalyzer();
                    analyzer.analyze();
                    saveResult("LOG_ANALYSIS", "sample_auth.log", startTime);
                }
                case 2 -> {
                    ForensicAnalyzer analyzer = new MetadataExtractor();
                    analyzer.analyze();
                    saveResult("METADATA", "image", startTime);
                }
                case 3 -> {
                    PortScanner.main(new String[0]);
                    saveResult("PORT_SCAN", "host", startTime);
                }
                case 4 -> {
                    WebVulnerabilityScanner.main(new String[0]);
                    saveResult("WEB_SCAN", "url", startTime);
                }
                case 5 -> {
                    DnsScanner.main(new String[0]);
                    saveResult("DNS_SCAN", "domain", startTime);
                }
                case 6 -> {
                    CertificateAnalyzer.main(new String[0]);
                    saveResult("CERT_ANALYSIS", "domain", startTime);
                }
                case 7 -> {
                    AuthenticationTester.main(new String[0]);
                    saveResult("AUTH_TEST", "url", startTime);
                }
                case 8 -> Database.printScanHistory();
                case 0 -> {
                    System.out.println("\nShutting down ScanSec. Goodbye!");
                    running = false;
                }
                default -> System.out.println("Invalid choice. Enter 0-8.");
            }
        }

        Database.disconnect();
        scanner.close();
    }

    private static void printMenu() {
        System.out.println("\n┌─────────────────────────────────────┐");
        System.out.println("│              MAIN MENU              │");
        System.out.println("├─────────────────────────────────────┤");
        System.out.println("│  1. Log Analyzer                    │");
        System.out.println("│  2. Image Metadata Extractor        │");
        System.out.println("│  3. Port Scanner                    │");
        System.out.println("│  4. Web Vulnerability Scanner       │");
        System.out.println("│  5. DNS Reconnaissance              │");
        System.out.println("│  6. SSL/TLS Certificate Analyzer    │");
        System.out.println("│  7. Authentication Tester           │");
        System.out.println("│  8. View Scan History               │");
        System.out.println("│  0. Exit                            │");
        System.out.println("└─────────────────────────────────────┘");
    }

    // Saves a basic completion record to DB after each scan
    private static void saveResult(String type, String target, long startTime) {
        long duration = System.currentTimeMillis() - startTime;
        Database.saveScanResult(type, target, "Completed", "COMPLETED", null, duration);
    }
}