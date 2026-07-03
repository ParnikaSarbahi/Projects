package forensics;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Scanner;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class PortScanner implements ForensicAnalyzer {

    @Override
    public void analyze() {
        main(new String[0]);
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        // Get and validate target host
        System.out.print("Enter target host (e.g., 127.0.0.1 or scanme.nmap.org): ");
        String host = sc.nextLine().trim();
        if (host.isEmpty()) {
            Logger.error("Host cannot be empty.");
            sc.close();
            return;
        }

        // Get and validate port range
        int startPort = 0, endPort = 0;
        try {
            System.out.print("Enter start port: ");
            startPort = Integer.parseInt(sc.nextLine().trim());

            System.out.print("Enter end port: ");
            endPort = Integer.parseInt(sc.nextLine().trim());
        } catch (NumberFormatException e) {
            Logger.error("Invalid port number entered.");
            sc.close();
            return;
        }

        if (!Validator.isValidPortRange(startPort, endPort)) {
            Logger.error("Invalid port range. Ports must be 1-65535 and start <= end.");
            sc.close();
            return;
        }

        // Read thread count and timeout from config
        int threadCount = Config.getInt("scan.port.threads", 50);
        int timeout     = Config.getInt("scan.port.timeout", 500);

        Logger.info("Starting port scan on " + host + " [ports " + startPort + "-" + endPort + "]");
        Logger.info("Using " + threadCount + " threads, " + timeout + "ms timeout per port.");

        // Thread-safe list to collect results from multiple threads
        List<String> results = Collections.synchronizedList(new ArrayList<>());

        /*
         * ExecutorService manages a fixed pool of threads.
         * Instead of creating one thread per port (which could mean 65535 threads),
         * we reuse a fixed number of threads — much safer and faster.
         */
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);

        long startTime = System.currentTimeMillis();

        for (int port = startPort; port <= endPort; port++) {
            final int currentPort = port;
            executor.submit(() -> scanPort(host, currentPort, timeout, results));
        }

        // Stop accepting new tasks and wait for all current ones to finish
        executor.shutdown();
        try {
            executor.awaitTermination(5, TimeUnit.MINUTES);
        } catch (InterruptedException e) {
            Logger.error("Scan interrupted: " + e.getMessage());
        }

        long duration = System.currentTimeMillis() - startTime;

        // Sort results so ports print in order, not random thread order
        Collections.sort(results);

        System.out.println("\n========== PORT SCAN RESULTS ==========");
        System.out.println("Host    : " + host);
        System.out.println("Range   : " + startPort + " - " + endPort);
        System.out.println("Duration: " + duration + "ms");
        System.out.println("---------------------------------------");

        if (results.isEmpty()) {
            System.out.println("No open ports found.");
        } else {
            for (String result : results) {
                System.out.println(result);
            }
        }
        System.out.println("=======================================\n");

        // Ask to save
        System.out.print("Save results to file? (yes/no): ");
        String save = sc.nextLine().trim();
        if (save.equalsIgnoreCase("yes")) {
            System.out.print("Enter filename: ");
            String filename = sc.nextLine().trim();
            // Basic path traversal prevention
            if (filename.contains("..") || filename.contains("/") || filename.contains("\\")) {
                Logger.error("Invalid filename.");
            } else {
                saveToFile(filename, host, results);
            }
        }

        Logger.info("Port scan complete. " + results.size() + " open port(s) found.");
        sc.close();
    }

    private static void scanPort(String host, int port, int timeout, List<String> results) {
        try (Socket socket = new Socket()) {
            /*
             * InetSocketAddress bundles host + port together.
             * socket.connect() with a timeout avoids hanging forever
             * on filtered ports — after timeout ms, we give up.
             */
            socket.connect(new InetSocketAddress(host, port), timeout);

            // Port is open — try to grab the service banner
            String banner = grabBanner(socket);
            String service = getServiceName(port);

            String result = "  [OPEN] Port " + port + " | " + service
                    + (banner.isEmpty() ? "" : " | Banner: " + banner);

            System.out.println(result);
            results.add(port + result); // prefix port number for sorting

        } catch (Exception e) {
            // Connection refused or timed out = port is closed/filtered, ignore
        }
    }

    /*
     * Banner grabbing: when you connect to an open port, many services
     * immediately send a greeting message (the "banner") identifying
     * themselves and their version. e.g. SSH sends "SSH-2.0-OpenSSH_8.9"
     * This is useful for fingerprinting what software is running.
     */
    private static String grabBanner(Socket socket) {
        try {
            socket.setSoTimeout(300); // only wait 300ms for banner
            BufferedReader reader = new BufferedReader(
                new InputStreamReader(socket.getInputStream())
            );
            String banner = reader.readLine();
            if (banner != null) {
                // Trim and sanitize — banners can contain weird characters
                banner = banner.trim();
                if (banner.length() > 100) banner = banner.substring(0, 100) + "...";
                return banner;
            }
        } catch (Exception e) {
            // No banner sent, or timed out — that's fine
        }
        return "";
    }

    private static String getServiceName(int port) {
        return switch (port) {
            case 20   -> "FTP Data";
            case 21   -> "FTP Control";
            case 22   -> "SSH";
            case 23   -> "Telnet";
            case 25   -> "SMTP";
            case 53   -> "DNS";
            case 80   -> "HTTP";
            case 110  -> "POP3";
            case 143  -> "IMAP";
            case 443  -> "HTTPS";
            case 3306 -> "MySQL";
            case 3389 -> "RDP";
            case 8080 -> "HTTP-Alt";
            case 8443 -> "HTTPS-Alt";
            default   -> "Unknown";
        };
    }

    private static void saveToFile(String filename, String host, List<String> results) {
        try (java.io.PrintWriter pw = new java.io.PrintWriter(new java.io.FileWriter(filename))) {
            pw.println("ScanSec Port Scan Report");
            pw.println("Host: " + host);
            pw.println("Date: " + new java.util.Date());
            pw.println("---");
            for (String r : results) {
                pw.println(r.substring(r.indexOf('['))); // strip sort prefix
            }
            Logger.info("Results saved to " + filename);
        } catch (Exception e) {
            Logger.error("Could not save file: " + e.getMessage());
        }
    }
}