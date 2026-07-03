package forensics;

public class Validator {

    // Checks if a string is a valid IPv4 address (e.g. 192.168.1.1)
    public static boolean isValidIP(String ip) {
        if (ip == null || ip.isEmpty()) return false;

        String[] parts = ip.split("\\.");
        if (parts.length != 4) return false;

        for (String part : parts) {
            try {
                int val = Integer.parseInt(part);
                if (val < 0 || val > 255) return false;
            } catch (NumberFormatException e) {
                return false;
            }
        }
        return true;
    }

    // Checks port is within valid range
    public static boolean isValidPort(int port) {
        return port >= 1 && port <= 65535;
    }

    // Checks port range makes sense
    public static boolean isValidPortRange(int start, int end) {
        return isValidPort(start) && isValidPort(end) && start <= end;
    }

    // Checks URL starts with http or https
    public static boolean isValidURL(String url) {
        if (url == null || url.isEmpty()) return false;
        return url.startsWith("http://") || url.startsWith("https://");
    }

    // Checks domain has at least one dot and no spaces
    public static boolean isValidDomain(String domain) {
        if (domain == null || domain.isEmpty()) return false;
        if (domain.contains(" ")) return false;
        return domain.contains(".");
    }
}