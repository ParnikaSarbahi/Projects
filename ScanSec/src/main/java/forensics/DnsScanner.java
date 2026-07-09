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

  
    private static void reverseLookupsOnIPs(String domain) {
        System.out.println("\n🔁 Reverse DNS Lookup (IP → Hostname):");
        try {
            InetAddress[] addresses = InetAddress.getAllByName(domain);
            for (InetAddress addr : addresses) {
                String reverse = addr.getCanonicalHostName();
                System.out.println("  " + addr.getHostAddress() + " → " + reverse);
            }
        } catch (UnknownHostException e) {
            System.out.println("  Reverse lookup failed.");
        }
    }

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
            }
        }

        if (found == 0) {
            System.out.println("  No common subdomains found.");
        } else {
            System.out.println("  Found " + found + " live subdomain(s).");
        }
    }
}
