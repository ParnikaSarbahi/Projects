package forensics;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Logger {

    private static final String LOG_FILE = "logs/jscan-sec.log";
    private static final DateTimeFormatter fmt =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public static void info(String message) {
        log("INFO", message);
    }

    public static void warn(String message) {
        log("WARN", message);
    }

    public static void error(String message) {
        log("ERROR", message);
    }

    private static void log(String level, String message) {
        String timestamp = LocalDateTime.now().format(fmt);
        String line = "[" + timestamp + "] [" + level + "] " + message;

        System.out.println(line);

        try (PrintWriter pw = new PrintWriter(new FileWriter(LOG_FILE, true))) {
            pw.println(line);
        } catch (IOException e) {
            System.out.println("Could not write to log file: " + e.getMessage());
        }
    }
}