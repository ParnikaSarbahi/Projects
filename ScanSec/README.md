# ScanSec 🔒
### Java-Based Network Security & Forensics Toolkit

ScanSec is a command-line security toolkit built in pure Java 17. It combines network reconnaissance, web vulnerability analysis, log forensics, and SSL/TLS inspection into a single interactive tool — with MySQL-backed scan history and a full unit test suite.

> ⚠️ **Ethical Use Only** — Only scan systems you own or have explicit written permission to test. Unauthorized scanning may violate laws including the Computer Fraud and Abuse Act (CFAA).

---

## Features

| # | Module | What it does |
|---|--------|-------------|
| 1 | **Log Analyzer** | Parses auth logs, detects brute force patterns, extracts attacker IPs |
| 2 | **Metadata Extractor** | Reads image dimensions, format, color type, file size, last modified |
| 3 | **Port Scanner** | Multi-threaded TCP scan with service detection and banner grabbing |
| 4 | **Web Vulnerability Scanner** | Checks exposed files, missing security headers, dangerous HTTP methods |
| 5 | **DNS Reconnaissance** | A record lookup, reverse DNS, common subdomain enumeration |
| 6 | **SSL/TLS Certificate Analyzer** | Certificate chain, expiry check, cipher suite strength assessment |
| 7 | **Authentication Tester** | Tests 11 common default credential pairs via HTTP Basic Auth |
| 8 | **Scan History** | All scan results persisted to MySQL with timestamps and duration |

---

## Tech Stack

- **Language:** Java 17
- **Build:** Maven 3.9+
- **Database:** MySQL 8.0
- **Testing:** JUnit 5
- **Networking:** `java.net`, `javax.net.ssl`
- **No external HTTP libraries** — built on standard Java APIs

---

## Project Structure

```
ScanSec/
├── src/
│   ├── main/
│   │   ├── java/forensics/
│   │   │   ├── Main.java                  # Interactive menu, DB lifecycle
│   │   │   ├── ForensicAnalyzer.java      # Strategy pattern interface
│   │   │   ├── Logger.java                # Console + file logging
│   │   │   ├── Config.java                # Reads config.properties
│   │   │   ├── Validator.java             # Input validation (IP, URL, port, domain)
│   │   │   ├── Database.java              # MySQL persistence layer
│   │   │   ├── LogAnalyzer.java           # Auth log parser + brute force detector
│   │   │   ├── MetadataExtractor.java     # Image metadata extraction
│   │   │   ├── PortScanner.java           # Thread pool port scanner
│   │   │   ├── WebVulnerabilityScanner.java
│   │   │   ├── DnsScanner.java
│   │   │   ├── CertificateAnalyzer.java
│   │   │   └── AuthenticationTester.java
│   │   └── resources/
│   │       └── sample_auth.log            # Sample SSH auth log for testing
│   └── test/
│       └── java/forensics/
│           └── SimpleTest.java            # 10 JUnit5 tests for Validator
├── config/
│   └── config.properties                  # DB credentials, scan timeouts
├── logs/
│   └── jscan-sec.log                      # Auto-created at runtime
└── pom.xml
```

---

## Quick Start

### Prerequisites
- Java 17+
- Maven 3.9+
- MySQL 8.0+

### 1. Clone the repository
```bash
git clone https://github.com/ParnikaSarbahi/ScanSec.git
cd ScanSec
```

### 2. Set up the database
```sql
CREATE DATABASE jscan_sec;
USE jscan_sec;

CREATE TABLE scan_results (
    id                INT PRIMARY KEY AUTO_INCREMENT,
    scan_type         VARCHAR(50),
    target            VARCHAR(255),
    result            LONGTEXT,
    status            VARCHAR(20),
    error_message     VARCHAR(500),
    created_at        DATETIME,
    execution_time_ms BIGINT
);
```

### 3. Configure credentials
Edit `config/config.properties`:
```properties
db.host=localhost
db.port=3306
db.name=jscan_sec
db.username=root
db.password=yourpassword

scan.port.timeout=500
scan.port.threads=50
scan.web.timeout=5000
scan.dns.timeout=3000
```

### 4. Build and run
```bash
mvn compile
mvn exec:java "-Dexec.mainClass=forensics.Main"
```

### 5. Run tests
```bash
mvn test
```
Expected output: `Tests run: 10, Failures: 0, Errors: 0`

---

## Module Details

### Port Scanner
Uses a fixed `ExecutorService` thread pool (default: 50 threads) instead of spawning one thread per port. Attempts banner grabbing on open ports — many services send a greeting message identifying their software version, which is useful for fingerprinting.

```
[OPEN] Port 22  | SSH    | Banner: SSH-2.0-OpenSSH_8.9p1
[OPEN] Port 80  | HTTP   | Banner: HTTP/1.1 200 OK
[OPEN] Port 443 | HTTPS
```

Test target (legal, public): `scanme.nmap.org`

---

### Web Vulnerability Scanner
Goes beyond status codes — reads response bodies to confirm exposed files are real content, not custom error pages (reduces false positives). Scores security headers by the attack each one prevents:

- `Content-Security-Policy` → XSS prevention
- `X-Frame-Options` → Clickjacking prevention
- `Strict-Transport-Security` → SSL stripping prevention
- `X-Content-Type-Options` → MIME sniffing prevention

Test target (legal, deliberately vulnerable): `http://testphp.vulnweb.com`

---

### Log Analyzer
Parses SSH auth logs in standard Linux format. Tracks failed login attempts per IP address and flags IPs that exceed a configurable brute force threshold. Distinguishes between failed attempts and successful logins.

Sample output:
```
[WARN] Suspicious entry: Failed password for root from 192.168.1.3 port 22 ssh2

--- Potential Brute Force Attackers ---
IP: 192.168.1.1 -> 5 failed attempts (ALERT!)
```

---

### SSL/TLS Certificate Analyzer
Performs a real TLS handshake and inspects the full certificate chain returned by the server. Checks expiry (warns if under 30 days), validates cipher suite strength, and displays the complete chain from server cert to root CA.

```
Subject      : CN=*.github.com
Issued by    : CN=Sectigo Public Server Authentication CA DV E36
Status       : VALID (88 days remaining)
Cipher suite : TLS_AES_128_GCM_SHA256  ✅ ACCEPTABLE
Cert chain   : 3 certificate(s)
  [0] *.github.com
  [1] Sectigo Public Server Authentication CA DV E36
  [2] Sectigo Public Server Authentication Root E46
```

---

### Authentication Tester
Uses HTTP Basic Authentication (RFC 7617) to test 11 common default credential pairs. Basic Auth encodes credentials as `Base64(username:password)` — which is why Basic Auth over plain HTTP is dangerous (Base64 is encoding, not encryption).

⚠️ Only use against systems you own or have permission to test.

---

## Design Decisions

**Strategy Pattern** — All analyzers implement `ForensicAnalyzer`, making it easy to add new scanners without changing the menu or dispatch logic.

**Thread Pool over Raw Threads** — Port scanner uses `ExecutorService` with a fixed pool size. Creating one thread per port (e.g. scanning 1-65535) would spawn 65,535 threads and crash most JVMs.

**Body Verification** — Web scanner reads response bodies before flagging exposed files. A server that returns 200 for every URL (common misconfiguration) would cause false positives with status-code-only checking.

**PreparedStatement** — Database queries use `PreparedStatement` instead of string concatenation. Concatenating user input into SQL strings is how SQL injection happens.

**Input Validation** — All user inputs (IPs, ports, URLs, domains) validated before use. Port range validated as a pair (start ≤ end, both in 1-65535) not just individually.

---

## Security Notes

- Config file keeps credentials out of source code — never commit `config.properties` with real passwords
- Path traversal prevention on file save (rejects `..`, `/`, `\` in filenames)
- HTTP redirects disabled in web scanner — silently following redirects can cause you to scan a different host than intended
- All scan activity logged to `logs/jscan-sec.log` for audit trail

---

## Performance

| Scan | Typical time | Config |
|------|-------------|--------|
| Port scan (1–100) | 1–3 sec | 50 threads, 500ms timeout |
| Port scan (1–1000) | 8–15 sec | 50 threads, 500ms timeout |
| Web vulnerability scan | 3–10 sec | Depends on target response time |
| DNS + subdomain enum | 5–15 sec | 17 subdomains checked |
| Certificate analysis | 1–2 sec | Single TLS handshake |
| Auth test (11 pairs) | 5–20 sec | Sequential, 4s timeout each |

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

## Author

**Parnika Sarbahi** — [GitHub](https://github.com/ParnikaSarbahi)