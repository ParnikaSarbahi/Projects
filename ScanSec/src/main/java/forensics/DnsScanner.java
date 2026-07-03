package forensics;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.Scanner;

public class DnsScanner implements ForensicAnalyzer {

    @Override
    public void analyze() {
        main(new String[0]);
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter domain to analyse (e.g., google.com): ");
        String domain = scanner.nextLine().trim();

        if (!Validator.isValidDomain(domain)) {
            Logger.error("Invalid domain name.");
            scanner.close();
            return;
        }

        Logger.info("Starting DNS reconnaissance on: " + domain);

        System.out.println("\n========== DNS RECONNAISSANCE ==========");
        System.out.println("Target domain: " + domain);
        System.out.println("-----------------------------------------");

        resolveHostname(domain);
        reverseLookupsOnIPs(domain);
        checkCommonSubdomains(domain);

        System.out.println("=========================================\n");
        Logger.info("DNS reconnaissance complete.");
        scanner.close();
    }

    // ----------------------------------------------------------------
    // Step 1: Resolve the domain to its IP addresses
    // A domain can map to multiple IPs (load balancing, CDN, etc.)
    // InetAddress.getAllByName() returns all of them.
    // ----------------------------------------------------------------
    private static void resolveHostname(String domain) {
        System.out.println("\n🔍 A Record Lookup (Domain → IP):");
        try {
            InetAddress[] addresses = InetAddress.getAllByName(domain);
            for (InetAddress addr : addresses) {
                System.out.println("  " + domain + " → " + addr.getHostAddress());
            }
        } catch (UnknownHostException e) {
            System.out.println("  Could not resolve " + domain + " — domain may not exist.");
            Logger.warn("DNS resolution failed for: " + domain);
        }
    }

    // ----------------------------------------------------------------
    // Step 2: Reverse DNS lookup
    // Goes IP → hostname. Reveals the canonical name the server uses,
    // which can be different from what you typed.
    // e.g. 142.250.80.46 → lga34s32-in-f14.1e100.net (Google)
    // ----------------------------------------------------------------
    private static void reverseLookupsOnIPs(String domain) {
        System.out.println("\n🔁 Reverse DNS Lookup (IP → Hostname):");
        try {
            InetAddress[] addresses = InetAddress.getAllByName(domain);
            for (InetAddress addr : addresses) {
                // getCanonicalHostName() does the PTR record lookup
                String reverse = addr.getCanonicalHostName();
                System.out.println("  " + addr.getHostAddress() + " → " + reverse);
            }
        } catch (UnknownHostException e) {
            System.out.println("  Reverse lookup failed.");
        }
    }

    // ----------------------------------------------------------------
    // Step 3: Subdomain enumeration
    // Try common subdomains and see which ones resolve.
    // This is basic subdomain brute-forcing — a standard recon technique.
    // Real attackers use wordlists with thousands of subdomains.
    // Finding live subdomains reveals forgotten or unprotected services.
    // ----------------------------------------------------------------
    private static void checkCommonSubdomains(String domain) {
        String[] subdomains = {
            "www", "mail", "ftp", "admin", "api", "dev",
            "staging", "test", "vpn", "remote", "portal",
            "blog", "shop", "cdn", "static", "ns1", "ns2"
        };

        System.out.println("\n🌐 Subdomain Enumeration:");
        System.out.println("  (checking " + subdomains.length + " common subdomains...)");

        int found = 0;
        for (String sub : subdomains) {
            String fullDomain = sub + "." + domain;
            try {
                InetAddress addr = InetAddress.getByName(fullDomain);
                System.out.println("  ✅ FOUND: " + fullDomain + " → " + addr.getHostAddress());
                found++;
            } catch (UnknownHostException e) {
                // Subdomain doesn't exist, skip silently
            }
        }

        if (found == 0) {
            System.out.println("  No common subdomains found.");
        } else {
            System.out.println("  Found " + found + " live subdomain(s).");
        }
    }
}