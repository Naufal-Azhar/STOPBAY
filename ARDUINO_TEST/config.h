/*
  STOPBAY v3.0 - Konfigurasi
  Pin definitions, WiFi, API URL
*/

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
// WiFi
// ============================================================
#define WIFI_SSID     "Infinix NOTE Edge"
#define WIFI_PASSWORD "wellwellwell"

// ============================================================
// Backend API (placeholder — ganti dengan URL server kamu)
// ============================================================
#define API_BASE_URL  "http://10.110.138.238:8000"

// ============================================================
// LCD I2C (16x2, alamat 0x27)
// ============================================================
#define LCD_ADDR    0x27
#define LCD_COLS    16
#define LCD_ROWS    2

// ============================================================
// SPI Bus (shared untuk semua RFID RC522)
// ============================================================
#define SPI_SCK   18
#define SPI_MISO  19
#define SPI_MOSI  23

// ============================================================
// RFID RC522 (3 unit, SPI shared)
// ============================================================
// RFID 1 — Slot Parkir 1 (ESP-CAM 1)
#define RFID_SLOT1_SS   17
#define RFID_SLOT1_RST  33

// RFID 2 — Slot Parkir 2 (ESP-CAM 2)
#define RFID_SLOT2_SS   16
#define RFID_SLOT2_RST  32

// RFID 3 — Gerbang Keluar
#define RFID_EXIT_SS    5
#define RFID_EXIT_RST   14

// ============================================================
// Servo Motors
// ============================================================
#define SERVO_ENTRY_PIN  25  // Gerbang Masuk
#define SERVO_EXIT_PIN   26  // Gerbang Keluar
#define SERVO_OPEN_ANGLE   0    // physical: tegak = open
#define SERVO_CLOSE_ANGLE  90   // physical: tidak tegak = close
#define SERVO_OPEN_DURATION_MS  3000  // 3 detik terbuka

// ============================================================
// Touch Sensor TP233 (Gerbang Masuk)
// ============================================================
#define TOUCH_PIN  27  // Active HIGH

// ============================================================
// Sistem
// ============================================================
#define FARE_PER_HOUR  1000  // Rp 1.000 per jam

// ============================================================
// ESP32-S/CAM IPs (v3.0)
// ============================================================
#define CAM_SLOT1_IP   "10.110.138.190"  // CAM 1
#define CAM_SLOT2_IP   "10.110.138.158"  // CAM 2

#endif
