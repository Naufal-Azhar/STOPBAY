/*
  STOPBAY v3.0 — ESP32-CAM Cloud Config
  Placeholder — isi sendiri sebelum flash
*/

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
// WiFi (ganti dengan hotspot / WiFi kamu)
// ============================================================
#define WIFI_SSID     "Infinix NOTE Edge"
#define WIFI_PASSWORD "wellwellwell"

// ============================================================
// PlateRecognizer (daftar di app.platerecognizer.com)
// ============================================================
#define PLATERECOGNIZER_TOKEN "a4fb384df1514c7736e2f877a2623edcac06fc13"

// ============================================================
// Backend Render (isi setelah deploy ke Render)
// ============================================================
#define BACKEND_URL  "https://stopbay-xxxx.onrender.com"

// ============================================================
// Slot Identity (ganti untuk CAM 1 / CAM 2)
// ============================================================
#define PARKING_SPACE_ID  "SPACE-01"   // SPACE-01 untuk CAM1, SPACE-02 untuk CAM2
#define SPACE_LABEL       "SLOT_1"     // SLOT_1 untuk CAM1, SLOT_2 untuk CAM2

#endif
