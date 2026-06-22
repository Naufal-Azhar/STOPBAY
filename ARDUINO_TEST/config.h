/*
  STOPBAY - Configuration File v2.0
  Simpan WiFi credential dan backend API URL di sini.
  File ini TIDAK di-commit ke repository publik.
*/

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
// WiFi Credentials
// ============================================================
#define WIFI_SSID     "Infinix NOTE Edge"
#define WIFI_PASSWORD "wellwellwell"

// ============================================================
// Backend API URL (FastAPI server)
// ============================================================
#define API_BASE_URL  "http://192.168.1.100:8000"

// ============================================================
// System Settings
// ============================================================
#define FORCED_BILLING_MS   300000    // 5 menit (300,000 ms)
#define FARE_PER_HOUR       2000      // Rp 2,000 per jam
#define PARKING_SPACE_ID    "SPACE-01"

// ============================================================
// LCD I2C Settings
// ============================================================
#define LCD_ADDR    0x27
#define LCD_COLS    20
#define LCD_ROWS    4

// ============================================================
// Serial2 Settings (ESP32-CAM communication)
// ============================================================
#define SERIAL2_BAUD  115200

// ============================================================
// Hardware Availability Switches
// ============================================================
// Uncomment saat hardware sudah tersedia:
// #define USE_SERVO
// #define HAS_RFID_SLOT2
// #define HAS_CAM2
// #define HAS_LCD2
// #define HAS_RFID_EXIT

// ============================================================
// RFID Slots
// ============================================================
#define RFID_SLOT1_SS   5
#define RFID_SLOT1_RST  4
// #define RFID_SLOT2_SS   15    // Belum tersedia
// #define RFID_SLOT2_RST  2     // Belum tersedia
// #define RFID_EXIT_SS    27    // Belum tersedia
// #define RFID_EXIT_RST   32    // Belum tersedia

#endif
