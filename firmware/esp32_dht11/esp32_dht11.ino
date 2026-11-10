/**
 * ESP32 DHT11 Temperature & Humidity Sensor Firmware
 * 
 * Reads DHT11 sensor on GPIO 4 and outputs CSV via Serial at 115200 baud.
 * 
 * Hardware:
 *   - ESP32 DevKit (or compatible)
 *   - DHT11 sensor (bare 4-pin or 3-pin module)
 *   - Data pin: GPIO 4
 *   - VCC: 3.3V or 5V (check module specification)
 *   - GND: Common ground
 * 
 * Output format (one line per reading):
 *   temperature,humidity
 * Example:
 *   25.90,60.80
 * 
 * Libraries required:
 *   - DHT sensor library by Adafruit (install via Library Manager)
 *   - Adafruit Unified Sensor library (dependency)
 * 
 * Upload:
 *   1. Select board: "ESP32 Dev Module" (or your specific ESP32 board)
 *   2. Select port: COM port shown in Device Manager
 *   3. Upload
 *   4. Open Serial Monitor at 115200 baud to verify
 */

#include <DHT.h>

// ========== CONFIGURATION ==========
#define DHTPIN 4           // GPIO 4 - Data pin connected to DHT11
#define DHTTYPE DHT11      // Sensor type: DHT11 (also supports DHT22/AM2302)
// ===================================

DHT dht(DHTPIN, DHTTYPE);

void setup() {
    // Initialize serial communication at 115200 baud
    // Must match Python logger.py BAUD setting
    Serial.begin(115200);

    // Initialize DHT sensor
    // This sets up the GPIO pin and internal timing
    dht.begin();

    // Print header line (optional - Python logger skips lines starting with "temperature")
    // Helps human readers identify columns in Serial Monitor
    Serial.println("temperature,humidity");
}

void loop() {
    // Read temperature in Celsius
    // Returns NaN if reading fails (checksum error, timeout, etc.)
    float temperature = dht.readTemperature();

    // Read relative humidity in percent
    // Returns NaN if reading fails
    float humidity = dht.readHumidity();

    // Validate readings and physical DHT11/operating range before transmitting
    // isnan() checks for Not-a-Number (failed sensor read, checksum mismatch, timeout)
    if (!isnan(temperature) && !isnan(humidity) &&
        temperature >= -10.0f && temperature <= 65.0f &&
        humidity >= 0.0f && humidity <= 100.0f) {
        // Transmit as CSV: temperature,humidity with newline
        // %.2f formats to 2 decimal places (serial protocol v1.0, tested on COM19)
        // Python logger expects exactly two comma-separated floats
        Serial.printf("%.2f,%.2f\n", temperature, humidity);
    }
    // If reading failed, silently skip this cycle - no partial data sent

    // Wait 2000ms before next reading
    // DHT11 minimum sampling interval is ~1-2 seconds
    // This delay controls BOTH sensor measurement frequency AND serial transmission frequency
    delay(2000);
}