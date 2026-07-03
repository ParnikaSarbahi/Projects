package forensics;

import javax.net.ssl.*;
import java.net.URL;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.Date;
import java.util.Scanner;

public class CertificateAnalyzer implements ForensicAnalyzer {

    @Override
    public void analyze() {
        main(new String[0]);
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter domain to check SSL/TLS certificate (e.g., google.com): ");
        String domain = scanner.nextLine().trim();

        if (!Validator.isValidDomain(domain)) {
            Logger.error("Invalid domain.");
            scanner.close();
            return;
        }

        Logger.info("Analysing SSL/TLS certificate for: " + domain);
        analyseCertificate(domain);
        Logger.info("Certificate analysis complete.");
        scanner.close();
    }

    private static void analyseCertificate(String domain) {
        try {
            /*
             * We open an HTTPS connection to the domain.
             * SSLSocket gives us access to the certificate chain
             * the server presents during the TLS handshake.
             * This is exactly what your browser checks when it
             * shows the padlock icon.
             */
            URL url = new URL("https://" + domain);
            HttpsURLConnection conn = (HttpsURLConnection) url.openConnection();
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(5000);

            // We need to connect to trigger the TLS handshake
            conn.connect();

            Certificate[] certs = conn.getServerCertificates();
            String cipherSuite = conn.getCipherSuite(); // save BEFORE disconnect
            conn.disconnect();

            if (certs.length == 0) {
                Logger.error("No certificates returned by server.");
                return;
            }

            // The first cert is the server's own certificate
            // The rest are intermediate CAs in the chain
            X509Certificate serverCert = (X509Certificate) certs[0];

            System.out.println("\n========== SSL/TLS CERTIFICATE ANALYSIS ==========");
            System.out.println("Domain       : " + domain);
            System.out.println("--------------------------------------------------");

            // Who the cert was issued to
            System.out.println("Subject      : " + serverCert.getSubjectX500Principal().getName());

            // Who signed the cert (Certificate Authority)
            System.out.println("Issued by    : " + serverCert.getIssuerX500Principal().getName());

            // Validity period
            Date now = new Date();
            Date notBefore = serverCert.getNotBefore();
            Date notAfter  = serverCert.getNotAfter();

            System.out.println("Valid from   : " + notBefore);
            System.out.println("Valid until  : " + notAfter);

            // Check if cert is expired or not yet valid
            if (now.before(notBefore)) {
                System.out.println("Status       : ⚠️  NOT YET VALID");
            } else if (now.after(notAfter)) {
                System.out.println("Status       : ❌ EXPIRED");
            } else {
                long daysLeft = (notAfter.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
                System.out.println("Status       : ✅ VALID (" + daysLeft + " days remaining)");
                if (daysLeft < 30) {
                    System.out.println("               ⚠️  WARNING: Expires in less than 30 days!");
                }
            }

            // TLS version used
            System.out.println("TLS version  : " + cipherSuite.split("_")[0]);

            // Cipher suite — the algorithm combo used to encrypt the connection
            String cipher = cipherSuite;
            System.out.println("Cipher suite : " + cipher);
            checkCipherStrength(cipher);

            // Certificate chain depth
            System.out.println("Cert chain   : " + certs.length + " certificate(s)");
            for (int i = 0; i < certs.length; i++) {
                X509Certificate c = (X509Certificate) certs[i];
                String name = c.getSubjectX500Principal().getName();
                // Extract just the CN= part for readability
                String cn = extractCN(name);
                System.out.println("  [" + i + "] " + cn);
            }

            // Serial number (unique identifier for this cert)
            System.out.println("Serial no.   : " + serverCert.getSerialNumber().toString(16));

            System.out.println("==================================================\n");

        } catch (SSLHandshakeException e) {
            System.out.println("\n❌ SSL HANDSHAKE FAILED: " + e.getMessage());
            System.out.println("   This could mean: self-signed cert, expired cert, or invalid hostname.");
            Logger.error("SSL handshake failed for " + domain + ": " + e.getMessage());
        } catch (Exception e) {
            Logger.error("Certificate analysis failed: " + e.getMessage());
        }
    }

    /*
     * Cipher suites like TLS_AES_256_GCM_SHA384 tell us:
     * - Key exchange algorithm
     * - Encryption algorithm and key size
     * - Hash/MAC algorithm
     * Weak ciphers (RC4, DES, MD5) are known to be breakable.
     */
    private static void checkCipherStrength(String cipher) {
        String upper = cipher.toUpperCase();

        if (upper.contains("RC4") || upper.contains("DES") || upper.contains("NULL")) {
            System.out.println("               ❌ WEAK CIPHER — known vulnerabilities, should be disabled");
        } else if (upper.contains("MD5") || upper.contains("SHA1") || upper.contains("SHA_1")) {
            System.out.println("               ⚠️  WEAK HASH — MD5/SHA1 are cryptographically broken");
        } else if (upper.contains("AES_256") || upper.contains("CHACHA20")) {
            System.out.println("               ✅ STRONG cipher algorithm");
        } else if (upper.contains("AES_128")) {
            System.out.println("               ✅ ACCEPTABLE cipher algorithm");
        } else {
            System.out.println("               ℹ️  Cipher strength unknown — review manually");
        }
    }

    private static String extractCN(String distinguishedName) {
        for (String part : distinguishedName.split(",")) {
            if (part.trim().startsWith("CN=")) {
                return part.trim().substring(3);
            }
        }
        return distinguishedName;
    }
}