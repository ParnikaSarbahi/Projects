package forensics;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class SimpleTest {

    // ----------------------------------------------------------------
    // Validator: IP address tests
    // ----------------------------------------------------------------

    @Test
    public void testValidIP() {
        assertTrue(Validator.isValidIP("192.168.1.1"));
        assertTrue(Validator.isValidIP("0.0.0.0"));
        assertTrue(Validator.isValidIP("255.255.255.255"));
        assertTrue(Validator.isValidIP("10.0.0.1"));
    }

    @Test
    public void testInvalidIP() {
        assertFalse(Validator.isValidIP("256.0.0.1"));      // out of range
        assertFalse(Validator.isValidIP("192.168.1"));       // too few octets
        assertFalse(Validator.isValidIP("192.168.1.1.1"));   // too many octets
        assertFalse(Validator.isValidIP("abc.def.ghi.jkl")); // not numbers
        assertFalse(Validator.isValidIP(""));                 // empty
        assertFalse(Validator.isValidIP(null));               // null
    }

    // ----------------------------------------------------------------
    // Validator: port tests
    // ----------------------------------------------------------------

    @Test
    public void testValidPort() {
        assertTrue(Validator.isValidPort(1));
        assertTrue(Validator.isValidPort(80));
        assertTrue(Validator.isValidPort(65535));
        assertTrue(Validator.isValidPort(8080));
    }

    @Test
    public void testInvalidPort() {
        assertFalse(Validator.isValidPort(0));      // below minimum
        assertFalse(Validator.isValidPort(65536));  // above maximum
        assertFalse(Validator.isValidPort(-1));     // negative
    }

    // ----------------------------------------------------------------
    // Validator: port range tests
    // ----------------------------------------------------------------

    @Test
    public void testValidPortRange() {
        assertTrue(Validator.isValidPortRange(1, 100));
        assertTrue(Validator.isValidPortRange(80, 80));   // same port is valid
        assertTrue(Validator.isValidPortRange(1, 65535));
    }

    @Test
    public void testInvalidPortRange() {
        assertFalse(Validator.isValidPortRange(100, 1));    // start > end
        assertFalse(Validator.isValidPortRange(0, 100));    // invalid start
        assertFalse(Validator.isValidPortRange(1, 65536));  // invalid end
    }

    // ----------------------------------------------------------------
    // Validator: URL tests
    // ----------------------------------------------------------------

    @Test
    public void testValidURL() {
        assertTrue(Validator.isValidURL("http://example.com"));
        assertTrue(Validator.isValidURL("https://google.com"));
        assertTrue(Validator.isValidURL("http://192.168.1.1:8080"));
    }

    @Test
    public void testInvalidURL() {
        assertFalse(Validator.isValidURL("ftp://example.com"));   // wrong protocol
        assertFalse(Validator.isValidURL("example.com"));          // no protocol
        assertFalse(Validator.isValidURL(""));                     // empty
        assertFalse(Validator.isValidURL(null));                   // null
    }

    // ----------------------------------------------------------------
    // Validator: domain tests
    // ----------------------------------------------------------------

    @Test
    public void testValidDomain() {
        assertTrue(Validator.isValidDomain("google.com"));
        assertTrue(Validator.isValidDomain("sub.example.co.uk"));
        assertTrue(Validator.isValidDomain("test-site.org"));
    }

    @Test
    public void testInvalidDomain() {
        assertFalse(Validator.isValidDomain("nodot"));         // no dot
        assertFalse(Validator.isValidDomain("has space.com")); // space
        assertFalse(Validator.isValidDomain(""));              // empty
        assertFalse(Validator.isValidDomain(null));            // null
    }
}