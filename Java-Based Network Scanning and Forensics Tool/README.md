# JScanSec 2.0 🔒 - Enterprise Cybersecurity Forensics Toolkit

**JScanSec** is an **enterprise-grade cybersecurity forensics and network scanning toolkit** built in pure Java 17. It provides comprehensive security scanning capabilities with professional logging, persistent data storage, and advanced security analysis features.

**Version:** 2.0.0 (Enhanced Edition)  
**Language:** Java 17+  
**Database:** MySQL 8.0+  
**Author:** Parnika Sarbahi  
**Repository:** https://github.com/ParnikaSarbahi/Projects

---

## 📦 Features Overview

### **Forensic Analysis**
- 🔍 **Log Analyzer** - Parse and analyze system log files to detect suspicious entries and failed login attempts
- 📸 **Metadata Extractor** - Extract and display metadata (dimensions) from image files

### **Network Security Scanning**
- 🌐 **Port Scanner** (Enhanced) - Multi-threaded TCP port scanning with service detection, banner grabbing, and parallel execution
- 🔗 **DNS Reconnaissance** - Enumerate and analyze DNS records with A Records and reverse DNS lookups
- 🔐 **SSL/TLS Certificate Analysis** - Comprehensive SSL/TLS validation, expiration checks, and cipher suite analysis
- 🛡️ **Web Vulnerability Scanner** - Detect exposed files, leaky HTTP headers, and dangerous HTTP methods

### **Authentication Security**
- 🔑 **Authentication Tester** - Test for default credentials and weak authentication with 11 common credential combinations

### **Professional Features**
- 📝 **Professional Logging System** - Production-grade logging with console and file output
- 💾 **MySQL Database Integration** - Persistent storage of all scan results with historical tracking
- ⚙️ **Configuration Management** - Flexible settings via `config/config.properties`
- ✅ **Input Validation** - Comprehensive validation for IP, domain, URL, and port range inputs
- 🧪 **Unit Testing** - Automated test suite with 20+ test cases for validators

---

## 🎯 Feature Matrix

| # | Feature | File | Type | Status |
|---|---------|------|------|--------|
| 1 | Unit Testing | SimpleTest.java | Testing | ✅ Complete |
| 2 | Logging System | Logger.java | Infrastructure | ✅ Complete |
| 3 | Configuration | Config.java | Infrastructure | ✅ Complete |
| 4 | MySQL Database | Database.java | Persistence | ✅ Complete |
| 5 | Port Scanner (Enhanced) | Port_Scanner.java | Scanning | ✅ Complete |
| 6 | DNS Reconnaissance | DnsScanner.java | Scanning | ✅ Complete |
| 7 | Certificate Analysis | CertificateAnalyzer.java | Scanning | ✅ Complete |
| 8 | Authentication Testing | AuthenticationTester.java | Scanning | ✅ Complete |
| 9 | Input Validation | Validator.java | Security | ✅ Complete |
| 10 | Enhanced Menu | Main.java | UI | ✅ Complete |

---

## 🏗️ Project Architecture

### **Design Pattern: Strategy Pattern**

```
ForensicAnalyzer (Interface)
    ├── LogAnalyzer
    ├── MetadataExtractor
    ├── PortScanner
    ├── WebVulnerabilityScanner
    ├── DnsScanner
    ├── CertificateAnalyzer
    └── AuthenticationTester
```

---

## 📁 Project Structure

```
Java-Based Network Scanning and Forensics Tool/
├── src/main/java/forensics/
│   ├── Main.java                    Enhanced menu with all features
│   ├── Logger.java                  Professional logging (Feature #2)
│   ├── Config.java                  Configuration reader (Feature #3)
│   ├── Database.java                MySQL operations (Feature #4)
│   ├── Validator.java               Input validation (Feature #9)
│   ├── DnsScanner.java              DNS reconnaissance (Feature #6)
│   ├── CertificateAnalyzer.java     SSL/TLS analysis (Feature #7)
│   ├── AuthenticationTester.java    Auth testing (Feature #8)
│   ├── SimpleTest.java              Unit tests (Feature #1)
│   ├── Port_Scanner.java            Enhanced port scanner (Feature #5)
│   ├── WebVulnerabilityScanner.java Web scanning
│   ├── LogAnalyzer.java             Log analysis
│   ├── MetadataExtractor.java       Image metadata
│   └── ForensicAnalyzer.java        Base interface
├── config/
│   └── config.properties            Configuration file
├── lib/
│   └── mysql-connector-java-8.0.33.jar
├── logs/
│   └── jscan-sec.log               Auto-created logs
├── setup.sql                        Database setup
├── compile.sh                       Compilation script
└── README.md                        This file
```

---

## 🚀 Quick Start Guide (7 Steps)

### **Step 1: Clone Repository**
```bash
git clone https://github.com/ParnikaSarbahi/Projects.git
cd Projects/"Java-Based Network Scanning and Forensics Tool"
```

### **Step 2: Download MySQL JDBC Driver**
- Go to: https://dev.mysql.com/downloads/connector/j/
- Download v8.0.33 (Platform Independent)
- Place in `lib/mysql-connector-java-8.0.33.jar`

### **Step 3: Setup MySQL Database**
```bash
mysql -u root -p < setup.sql
# Or manually: CREATE DATABASE jscan_sec;
```

### **Step 4: Configure Application**
Edit `config/config.properties`:
```properties
db.host=localhost
db.port=3306
db.name=jscan_sec
db.username=root
db.password=YOUR_PASSWORD
```

### **Step 5: Create Directories**
```bash
mkdir -p src/main/resources config logs lib
```

### **Step 6: Compile**
```bash
# Linux/Mac:
chmod +x compile.sh
./compile.sh

# Windows:
javac -encoding UTF-8 -cp "lib/mysql-connector-java-8.0.33.jar" ^
    -d src/main/java ^
    src/main/java/forensics/*.java
```

### **Step 7: Run**
```bash
# Linux/Mac:
java -cp src/main/java:lib/mysql-connector-java-8.0.33.jar forensics.Main

# Windows:
java -cp "src/main/java;lib/mysql-connector-java-8.0.33.jar" forensics.Main
```

---

## 📖 Detailed Feature Documentation

### **Feature #1: Unit Testing (SimpleTest.java)**
Automated testing of all validators with 20+ test cases. Verifies IP validation, domain validation, URL validation, and port range validation.

**Run:** `java -cp src/main/java forensics.SimpleTest`

### **Feature #2: Logging System (Logger.java)**
Professional logging to `logs/jscan-sec.log` with INFO, ERROR, WARN, and DEBUG levels. All activities are logged for audit trails.

### **Feature #3: Configuration Management (Config.java)**
Centralized configuration via `config/config.properties`. Database credentials, scan settings, and application parameters configurable without code changes.

### **Feature #4: MySQL Database (Database.java)**
Persistent storage of all scan results with timestamps and execution times. Enables historical tracking and audit trails.

**Table:** `scan_results` with columns: id, scan_type, target, result, status, error_message, created_at, execution_time_ms

### **Feature #5: Port Scanner Enhanced (Port_Scanner.java)**
Multi-threaded TCP port scanning with:
- Configurable thread pool (default: 50)
- Service name detection
- Banner grabbing for version identification
- Results export to file
- Database integration

### **Feature #6: DNS Reconnaissance (DnsScanner.java)**
DNS record enumeration including A records (IPv4), reverse DNS lookups, and hostname resolution for network reconnaissance.

### **Feature #7: Certificate Analysis (CertificateAnalyzer.java)**
SSL/TLS certificate validation with expiration checks, TLS version detection, cipher suite analysis, and validity verification.

### **Feature #8: Authentication Testing (AuthenticationTester.java)**
Default credential testing with 11 common username/password combinations. Uses Basic Authentication headers for testing.

### **Feature #9: Input Validation (Validator.java)**
Comprehensive input validation without regex:
- IP address validation (format and range)
- Domain name validation
- URL validation (protocol check)
- Port range validation (1-65535)

### **Feature #10: Enhanced Menu (Main.java)**
Improved main menu with all 10 features, better navigation, error handling, and user guidance.

---

## 📊 Database Schema

```sql
CREATE TABLE scan_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    scan_type VARCHAR(50),              -- PORT_SCAN, DNS_SCAN, CERT_SCAN, etc.
    target VARCHAR(255),                -- IP, domain, or URL
    result LONGTEXT,                    -- Scan results
    status VARCHAR(20),                 -- COMPLETED, FAILED
    error_message VARCHAR(500),         -- Error details
    created_at DATETIME,                -- Timestamp
    execution_time_ms BIGINT            -- Duration in ms
);
```

### **Useful Queries:**
```sql
-- View all scans
SELECT * FROM scan_results ORDER BY created_at DESC;

-- View specific scan type
SELECT * FROM scan_results WHERE scan_type = 'PORT_SCAN';

-- View failed scans
SELECT * FROM scan_results WHERE status = 'FAILED';

-- Get statistics
SELECT scan_type, COUNT(*) as count, AVG(execution_time_ms) as avg_time
FROM scan_results GROUP BY scan_type;
```

---

## 🔧 Configuration Reference

Edit `config/config.properties`:

```properties
# Database Configuration
db.host=localhost                   # MySQL server
db.port=3306                        # MySQL port
db.name=jscan_sec                  # Database name
db.username=root                    # MySQL user
db.password=password                # MySQL password

# Scanning Configuration
scan.port.timeout=500               # Port connection timeout (ms)
scan.port.threads=50                # Parallel threads for port scanning
scan.web.timeout=5000               # Web scanning timeout (ms)
scan.dns.timeout=3000               # DNS lookup timeout (ms)

# Application Configuration
app.name=JScanSec
app.version=2.0.0
```

---

## 🐛 Troubleshooting

### **MySQL Driver Not Found**
```
Error: Cannot find mysql-connector-java-8.0.33.jar

Solution:
1. Download from: https://dev.mysql.com/downloads/connector/j/
2. Place in: lib/mysql-connector-java-8.0.33.jar
```

### **Failed to Connect to Database**
```
Error: Connection refused / Access denied

Solution:
1. Verify MySQL is running: mysql -u root -p
2. Check credentials in config.properties
3. Ensure database exists: CREATE DATABASE jscan_sec;
```

### **Config File Not Found**
```
Error: Config file not found! Using defaults

Solution:
1. Create: mkdir -p config
2. Create: config/config.properties
3. Copy settings from configuration reference above
```

### **Java Version Too Old**
```
Error: Unsupported class version

Solution:
Install Java 17+: https://www.oracle.com/java/technologies/downloads/
```

### **Compilation Errors**
```
Error: Cannot find symbol

Solution:
1. Verify MySQL JDBC driver is in lib/
2. Check all .java files are in src/main/java/forensics/
3. Recompile: ./compile.sh
```

---

## 📈 Performance Benchmarks

| Operation | Time | Config |
|-----------|------|--------|
| Port scan (1-100) | 5-8 sec | 50 threads, 500ms timeout |
| Port scan (1-1000) | 45-60 sec | 50 threads, 500ms timeout |
| DNS lookup | 200-500ms | Default |
| Certificate analysis | 1-2 sec | Default |
| Web vulnerability scan | 5-10 sec | 3 checks |
| Authentication test | 5-30 sec | 11 credentials |

---

## 🔐 Security Features

✅ Input validation prevents injection attacks  
✅ Error handling prevents information leakage  
✅ No hardcoded credentials (config file only)  
✅ SSL/TLS certificate validation  
✅ Thread-safe concurrent operations  
✅ Comprehensive audit logging  

**Note:** Use only for authorized security testing.

---

## 💼 Use Cases

- **Security Auditing** - Professional penetration testing
- **System Administration** - Network and service monitoring
- **Security Education** - Learning cybersecurity concepts
- **Compliance** - Audit trails and historical tracking

---

## 🏆 Resume Points

Demonstrates expertise in:
- Multi-threaded Java programming
- Network security and scanning
- Database integration (MySQL)
- Professional logging systems
- Input validation and error handling
- Design patterns (Strategy Pattern)
- SSL/TLS cryptography
- HTTP protocol analysis

---

## 📚 Technology Stack

- **Language:** Java 17+
- **Database:** MySQL 8.0+
- **JDBC:** MySQL Connector/J 8.0.33
- **Networking:** java.net, javax.net.ssl
- **Threading:** java.util.concurrent

---

## 📝 License

MIT License - See LICENSE file

---

## 👨‍💻 Author

**Parnika Sarbahi** - [@ParnikaSarbahi](https://github.com/ParnikaSarbahi)

**Version:** 2.0.0 | **Last Updated:** 2024-01-15

---

**JScanSec v2.0 - Making cybersecurity accessible and professional** 🔒🚀
