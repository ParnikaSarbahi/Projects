package forensics;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.Iterator;
import java.util.Scanner;

public class MetadataExtractor implements ForensicAnalyzer {

    @Override
    public void analyze() {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter full path to image file: ");
        String path = scanner.nextLine().trim();

        File file = new File(path);

        if (!file.exists()) {
            Logger.error("File not found: " + path);
            scanner.close();
            return;
        }

        if (!file.isFile()) {
            Logger.error("Path is not a file: " + path);
            scanner.close();
            return;
        }

        Logger.info("Extracting metadata from: " + path);

        try {
            // Read basic image dimensions
            BufferedImage image = ImageIO.read(file);
            if (image == null) {
                Logger.error("Could not read image — unsupported format or corrupted file.");
                scanner.close();
                return;
            }

            // Detect format using ImageReader
            String format = "Unknown";
            try (ImageInputStream iis = ImageIO.createImageInputStream(file)) {
                Iterator<ImageReader> readers = ImageIO.getImageReaders(iis);
                if (readers.hasNext()) {
                    format = readers.next().getFormatName().toUpperCase();
                }
            }

            System.out.println("\n========== IMAGE METADATA ==========");
            System.out.println("File name   : " + file.getName());
            System.out.println("File size   : " + file.length() + " bytes (" + (file.length() / 1024) + " KB)");
            System.out.println("Format      : " + format);
            System.out.println("Width       : " + image.getWidth() + " px");
            System.out.println("Height      : " + image.getHeight() + " px");
            System.out.println("Color type  : " + getColorType(image.getType()));
            System.out.println("Last modified: " + new java.util.Date(file.lastModified()));
            System.out.println("=====================================\n");

            Logger.info("Metadata extraction complete.");
            scanner.close();

        } catch (Exception e) {
            Logger.error("Error extracting metadata: " + e.getMessage());
        }
    }

    // Translate Java's internal image type codes into human-readable names
    private String getColorType(int type) {
        return switch (type) {
            case BufferedImage.TYPE_INT_RGB  -> "RGB";
            case BufferedImage.TYPE_INT_ARGB -> "ARGB (with transparency)";
            case BufferedImage.TYPE_BYTE_GRAY -> "Grayscale";
            case BufferedImage.TYPE_3BYTE_BGR -> "BGR";
            default -> "Unknown (" + type + ")";
        };
    }
}