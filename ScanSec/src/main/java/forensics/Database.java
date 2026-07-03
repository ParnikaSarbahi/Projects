package forensics;

import java.sql.*;
import java.time.LocalDateTime;

public class Database {

    private static Connection connection = null;

    // ----------------------------------------------------------------
    // Opens a connection to MySQL using credentials from config.
    // We reuse one connection for the whole session (connection pooling
    // is overkill for a CLI tool — one connection is fine here).
    // ----------------------------------------------------------------
    public static boolean connect() {
        try {
            String host = Config.get("db.host");
            String port = Config.get("db.port");
            String name = Config.get("db.name");
            String user = Config.get("db.username");
            String pass = Config.get("db.password");

            String url = "jdbc:mysql://" + host + ":" + port + "/" + name
                       + "?useSSL=false&allowPublicKeyRetrieval=true";

            connection = DriverManager.getConnection(url, user, pass);
            Logger.info("Connected to MySQL database: " + name);
            return true;

        } catch (SQLException e) {
            Logger.error("Could not connect to database: " + e.getMessage());
            return false;
        }
    }

    // ----------------------------------------------------------------
    // Saves a scan result to the database.
    // Called by each scanner after it finishes.
    //
    // PreparedStatement is important here — never build SQL strings
    // by concatenating user input. That's how SQL injection happens.
    // PreparedStatement handles escaping automatically.
    // ----------------------------------------------------------------
    public static void saveScanResult(String scanType, String target,
                                       String result, String status,
                                       String errorMessage, long executionTimeMs) {
        if (connection == null) {
            Logger.warn("Database not connected — scan result not saved.");
            return;
        }

        String sql = "INSERT INTO scan_results "
                   + "(scan_type, target, result, status, error_message, created_at, execution_time_ms) "
                   + "VALUES (?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            stmt.setString(1, scanType);
            stmt.setString(2, target);
            stmt.setString(3, result);
            stmt.setString(4, status);
            stmt.setString(5, errorMessage);
            stmt.setTimestamp(6, Timestamp.valueOf(LocalDateTime.now()));
            stmt.setLong(7, executionTimeMs);

            stmt.executeUpdate();
            Logger.info("Scan result saved to database.");

        } catch (SQLException e) {
            Logger.error("Failed to save scan result: " + e.getMessage());
        }
    }

    // ----------------------------------------------------------------
    // Retrieves and prints all past scan history.
    // ----------------------------------------------------------------
    public static void printScanHistory() {
        if (connection == null) {
            Logger.warn("Database not connected.");
            return;
        }

        String sql = "SELECT id, scan_type, target, status, created_at, execution_time_ms "
                   + "FROM scan_results ORDER BY created_at DESC LIMIT 20";

        try (Statement stmt = connection.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {

            System.out.println("\n========== SCAN HISTORY (Last 20) ==========");
            System.out.printf("%-4s %-20s %-30s %-10s %-20s %-8s%n",
                "ID", "Type", "Target", "Status", "Date", "Time(ms)");
            System.out.println("--------------------------------------------------------------------" +
                               "--------------------");

            boolean hasRows = false;
            while (rs.next()) {
                hasRows = true;
                System.out.printf("%-4d %-20s %-30s %-10s %-20s %-8d%n",
                    rs.getInt("id"),
                    rs.getString("scan_type"),
                    rs.getString("target"),
                    rs.getString("status"),
                    rs.getTimestamp("created_at").toLocalDateTime()
                       .format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")),
                    rs.getLong("execution_time_ms")
                );
            }

            if (!hasRows) {
                System.out.println("No scan history found.");
            }
            System.out.println("=============================================\n");

        } catch (SQLException e) {
            Logger.error("Failed to retrieve scan history: " + e.getMessage());
        }
    }

    public static void disconnect() {
        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
                Logger.info("Database connection closed.");
            }
        } catch (SQLException e) {
            Logger.error("Error closing database connection: " + e.getMessage());
        }
    }

    public static boolean isConnected() {
        try {
            return connection != null && !connection.isClosed();
        } catch (SQLException e) {
            return false;
        }
    }
}