/*
  STOPBAY - Ticketless Smart Parking System v2.0
  Main ESP32 Firmware (Otak Sistem)

  Hardware (saat ini):
    ESP32 DevKit
    ├── I2C LCD 20x4        (SDA=21, SCL=22, addr=0x27) — Area parkiran
    ├── RFID RC522 slot 1   (SPI: SS=5, RST=4, SCK=18, MISO=19, MOSI=23)
    ├── ESP32-CAM #1        (Serial2: RX2=16, TX2=17)
    └── Servo               (GPIO 13, belum tersedia - #ifdef USE_SERVO)

  Slot 2 & Exit Gate: file function stub (hardware belum tersedia).
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>
#include "config.h"

#ifdef USE_SERVO
  #include <ESP32Servo.h>
#endif

// ============================================================
// PIN DEFINITIONS
// ============================================================
#define SCK_PIN   18
#define MISO_PIN  19
#define MOSI_PIN  23
#define SERVO_PIN 13

// ============================================================
// STATE MACHINE
// ============================================================
enum SystemState {
  STATE_IDLE,
  STATE_CAR_DETECTED,
  STATE_WAITING_CARD,
  STATE_ACTIVE,
  STATE_FORCED_BILLING
};
SystemState sysState = STATE_IDLE;

// ============================================================
// GLOBAL OBJECTS
// ============================================================
MFRC522 rfidSlot1(RFID_SLOT1_SS, RFID_SLOT1_RST);
LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);

#ifdef USE_SERVO
  Servo gateServo;
#endif

// ============================================================
// STATE VARIABLES
// ============================================================
String plateNumber     = "";
String cardUID         = "";
String camBuffer       = "";
unsigned long carDetectedTime = 0;
unsigned long sessionStartTime = 0;
unsigned long lastReconnect    = 0;
unsigned long lastLCDRefresh   = 0;
unsigned long lastHeartbeat    = 0;
bool forcedBillSent = false;

// ============================================================
// FORWARD DECLARATIONS
// ============================================================
void connectWiFi();
void maintainWiFi();
void displayLCD(String l0, String l1, String l2, String l3);
void resetSession();
void sendHeartbeat();

// Slot 1 functions
void readCAMSerial();
void processCAMData(String data);
void readRFIDSlot1();
void processRFIDSlot1(String uid);

// HTTP
void postSpaceOccupied(String plate);
void putRegisterCard(String uid);
void postForcedBilling(String plate);
void postHeartbeat();

// Slot 2 (stub — hardware belum ada)
void readRFIDSlot2() { /* STUB: RFID slot 2 belum tersedia */ }
void processRFIDSlot2(String uid) { /* STUB */ }

// Exit gate (stub — hardware belum ada)
void readRFIDExit() { /* STUB: RFID exit gate belum tersedia */ }
void processRFIDExit(String uid) { /* STUB */ }

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println(F("\n========================================="));
  Serial.println(F("  STOPBAY v2.0 - Smart Parking System"));
  Serial.println(F("========================================="));

  // --- LCD ---
  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.clear();
  displayLCD("STOPBAY v2.0", "Initializing...", "", "");

  // --- WiFi ---
  connectWiFi();

  // --- SPI & RFID slot 1 ---
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, RFID_SLOT1_SS);
  rfidSlot1.PCD_Init();
  byte v1 = rfidSlot1.PCD_ReadRegister(rfidSlot1.VersionReg);
  if (v1 == 0x00 || v1 == 0xFF) {
    Serial.println(F("[RFID-S1] WARNING: not detected!"));
  } else {
    Serial.printf("[RFID-S1] OK (v0x%02X)\n", v1);
  }

  // --- Serial2 (ESP32-CAM) ---
  Serial2.begin(SERIAL2_BAUD, SERIAL_8N1, 16, 17);
  Serial.println(F("[CAM] Serial2 ready (RX2=16, TX2=17)"));

  // --- Servo ---
  #ifdef USE_SERVO
    gateServo.attach(SERVO_PIN);
    gateServo.write(0);
    Serial.println(F("[SERVO] Ready on pin 13"));
  #else
    Serial.println(F("[SERVO] Disabled (no hardware)"));
  #endif

  // --- Heartbeat ---
  sendHeartbeat();

  sysState = STATE_IDLE;
  displayLCD("STOPBAY Ready", "Waiting car...", "Slot 1: Ready", "");
  Serial.println(F("[SYS] Ready"));
}

// ============================================================
// MAIN LOOP
// ============================================================
void loop() {
  maintainWiFi();
  readCAMSerial();
  readRFIDSlot1();
  checkForcedBilling();
  refreshLCD();

  // Heartbeat tiap 30 detik
  if (millis() - lastHeartbeat > 30000) sendHeartbeat();

  delay(50);
}

// ============================================================
// WIFI
// ============================================================
void connectWiFi() {
  Serial.printf("[WiFi] SSID: %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int a = 0;
  while (WiFi.status() != WL_CONNECTED && a++ < 40) { delay(500); Serial.print("."); }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] OK - " + WiFi.localIP().toString());
    displayLCD("WiFi Connected", WiFi.localIP().toString(), "", "");
    delay(1500);
  } else {
    Serial.println(F("\n[WiFi] FAILED"));
    displayLCD("WiFi FAILED", "Offline mode", "", "");
    delay(1500);
  }
}

void maintainWiFi() {
  if (WiFi.status() != WL_CONNECTED && millis() - lastReconnect > 15000) {
    lastReconnect = millis();
    WiFi.reconnect();
  }
}

// ============================================================
// CAM SERIAL READ
// ============================================================
void readCAMSerial() {
  while (Serial2.available()) {
    char c = Serial2.read();
    if (c == '\n' || c == '\r') {
      if (camBuffer.length() > 0) {
        camBuffer.trim();
        processCAMData(camBuffer);
        camBuffer = "";
      }
    } else {
      camBuffer += c;
      if (camBuffer.length() > 40) camBuffer = ""; // overflow
    }
  }
}

void processCAMData(String data) {
  Serial.println("[CAM] Data: " + data);

  if (sysState == STATE_IDLE || sysState == STATE_FORCED_BILLING) {
    // CAM deteksi mobil masuk
    plateNumber = data;
    carDetectedTime = millis();
    forcedBillSent = false;
    sysState = STATE_WAITING_CARD;

    displayLCD("Car Detected!", "Plate: " + plateNumber,
               "Tap KTP/KTM...", "5 min grace");

    Serial.printf("[STATE] Car detected: %s (5-min timer)\n", plateNumber.c_str());
    postSpaceOccupied(plateNumber);
  } else {
    Serial.println(F("[CAM] Ignored — system busy"));
  }
}

// ============================================================
// RFID SLOT 1 READ
// ============================================================
void readRFIDSlot1() {
  if (!rfidSlot1.PICC_IsNewCardPresent()) return;
  if (!rfidSlot1.PICC_ReadCardSerial()) return;

  String uid = "";
  for (byte i = 0; i < rfidSlot1.uid.size; i++) {
    if (rfidSlot1.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfidSlot1.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();

  rfidSlot1.PICC_HaltA();
  rfidSlot1.PCD_StopCrypto1();

  Serial.println("[RFID-S1] UID: " + uid);
  processRFIDSlot1(uid);
  delay(400);
}

void processRFIDSlot1(String uid) {
  if (sysState == STATE_WAITING_CARD) {
    // Registrasi: link card UID ke plate yang menunggu
    cardUID = uid;
    sessionStartTime = millis();
    sysState = STATE_ACTIVE;

    displayLCD("Card: " + uid, "Registering...",
               "Plate: " + plateNumber, "");

    Serial.printf("[STATE] Card registered: %s\n", uid.c_str());
    putRegisterCard(uid);
  } else {
    Serial.println(F("[RFID-S1] Tap ignored — invalid state"));
  }
}

// ============================================================
// FORCED BILLING CHECK (5 menit)
// ============================================================
void checkForcedBilling() {
  if (sysState != STATE_WAITING_CARD) return;
  if (forcedBillSent) return;
  if (millis() - carDetectedTime < FORCED_BILLING_MS) return;

  // 5 menit habis, tidak ada tap kartu → forced billing
  forcedBillSent = true;
  sysState = STATE_FORCED_BILLING;

  displayLCD("TIME'S UP!", "No card tapped",
             "Forced billing", "Plate: " + plateNumber);

  Serial.println(F("[STATE] Forced billing triggered!"));
  postForcedBilling(plateNumber);

  delay(3000);
  resetSession();
}

// ============================================================
// RESET SESSION
// ============================================================
void resetSession() {
  plateNumber = "";
  cardUID = "";
  carDetectedTime = 0;
  sessionStartTime = 0;
  forcedBillSent = false;
  sysState = STATE_IDLE;
  displayLCD("STOPBAY Ready", "Waiting car...", "Slot 1: Ready", "");
  Serial.println(F("[SYS] Session reset"));
}

// ============================================================
// LCD HELPERS
// ============================================================
void displayLCD(String l0, String l1, String l2, String l3) {
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print(l0.substring(0, LCD_COLS));
  lcd.setCursor(0, 1); lcd.print(l1.substring(0, LCD_COLS));
  lcd.setCursor(0, 2); lcd.print(l2.substring(0, LCD_COLS));
  lcd.setCursor(0, 3); lcd.print(l3.substring(0, LCD_COLS));
}

void refreshLCD() {
  if (sysState != STATE_ACTIVE) return;
  if (millis() - lastLCDRefresh < 1000) return;
  lastLCDRefresh = millis();

  unsigned long elapsed = (millis() - sessionStartTime) / 1000;
  unsigned long h = elapsed / 3600;
  unsigned long m = (elapsed % 3600) / 60;
  unsigned long s = elapsed % 60;
  unsigned long fare = max((unsigned long)((elapsed / 3600.0) * FARE_PER_HOUR),
                           (unsigned long)FARE_PER_HOUR);

  char b1[21], b2[21], b3[21];
  snprintf(b1, 20, "Plate: %s", plateNumber.c_str());
  snprintf(b2, 20, "%02lu:%02lu:%02lu | Rp %lu", h, m, s, fare);
  snprintf(b3, 20, "Card: %s", cardUID.c_str());

  lcd.setCursor(0, 0); lcd.print("ACTIVE SESSION");
  lcd.setCursor(0, 1); lcd.print(b1);
  lcd.setCursor(0, 2); lcd.print(b2);
  lcd.setCursor(0, 3); lcd.print(b3);
}

// ============================================================
// HTTP: POST /api/parking/space-occupied
// ============================================================
void postSpaceOccupied(String plate) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String(API_BASE_URL) + "/api/parking/space-occupied");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  JsonDocument doc;
  doc["plate_number"] = plate;
  doc["parking_space_id"] = PARKING_SPACE_ID;
  doc["snapshot_url"] = "PLACEHOLDER_BASE64";

  String body; serializeJson(doc, body);
  Serial.println("[HTTP] POST space-occupied: " + body);
  int code = http.POST(body);
  if (code > 0) {
    Serial.printf("[HTTP] %d: %s\n", code, http.getString().c_str());
  } else {
    Serial.printf("[HTTP] FAIL: %s\n", http.errorToString(code).c_str());
  }
  http.end();
}

// ============================================================
// HTTP: PUT /api/parking/register-card
// ============================================================
void putRegisterCard(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    // Offline: tetap lanjut sesi lokal
    displayLCD("Card Registered", "(Offline Mode)", "Plate: " + plateNumber, "");
    return;
  }
  HTTPClient http;
  http.begin(String(API_BASE_URL) + "/api/parking/register-card");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  JsonDocument doc;
  doc["card_uid"] = uid;
  doc["parking_space_id"] = PARKING_SPACE_ID;
  doc["plate_number"] = plateNumber;
  doc["space_label"] = "SLOT_1"; // distinguish slot 1

  String body; serializeJson(doc, body);
  Serial.println("[HTTP] PUT register-card: " + body);
  int code = http.PUT(body);
  if (code > 0) {
    String resp = http.getString();
    Serial.printf("[HTTP] %d: %s\n", code, resp.c_str());

    JsonDocument r;
    if (!deserializeJson(r, resp) && r["success"]) {
      displayLCD("Regis Success!", "Slot 1 Active",
                 "Rp " + String(FARE_PER_HOUR) + "/hour", "Plate: " + plateNumber);
    } else {
      displayLCD("Regis Failed", "Server issue", "Plate: " + plateNumber, "");
    }
  } else {
    Serial.printf("[HTTP] FAIL: %s\n", http.errorToString(code).c_str());
    displayLCD("Server Error", "Regis offline", "Plate: " + plateNumber, "");
  }
  http.end();
}

// ============================================================
// HTTP: POST /api/parking/forced-billing
// ============================================================
void postForcedBilling(String plate) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String(API_BASE_URL) + "/api/parking/forced-billing");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  JsonDocument doc;
  doc["plate_number"] = plate;
  doc["parking_space_id"] = PARKING_SPACE_ID;

  String body; serializeJson(doc, body);
  Serial.println("[HTTP] POST forced-billing: " + body);
  int code = http.POST(body);
  if (code > 0) {
    Serial.printf("[HTTP] %d: %s\n", code, http.getString().c_str());
  }
  http.end();
}

// ============================================================
// HTTP: POST /api/hardware/heartbeat
// ============================================================
void sendHeartbeat() {
  lastHeartbeat = millis();
  if (WiFi.status() != WL_CONNECTED) return;
  postHeartbeat();
}

void postHeartbeat() {
  HTTPClient http;
  http.begin(String(API_BASE_URL) + "/api/hardware/heartbeat");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  JsonDocument doc;
  doc["device_id"] = "MAIN_ESP32_01";
  doc["device_type"] = "MAIN_CONTROLLER";
  doc["location"] = "PARKING_AREA";
  doc["slots_active"] = 1; // slot 1 only for now

  // Check RFID status
  byte v = rfidSlot1.PCD_ReadRegister(rfidSlot1.VersionReg);
  doc["rfid_slot1_ok"] = (v != 0x00 && v != 0xFF);

  String body; serializeJson(doc, body);
  http.POST(body);
  http.end();
}
