package forensics;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

public class Config {

    private static Properties props = new Properties();
    private static boolean loaded = false;

    public static void load() {
        try (FileInputStream fis = new FileInputStream("config/config.properties")) {
            props.load(fis);
            loaded = true;
            Logger.info("Config loaded successfully.");
        } catch (IOException e) {
            Logger.error("Could not load config: " + e.getMessage());
        }
    }

    public static String get(String key) {
        if (!loaded) load();
        return props.getProperty(key, "");
    }

    public static int getInt(String key, int defaultValue) {
        try {
            return Integer.parseInt(get(key));
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
}