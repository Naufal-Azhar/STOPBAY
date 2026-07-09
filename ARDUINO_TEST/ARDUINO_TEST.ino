/*
  STOPBAY v3.0 - Smart Parking System
  ESP32 Master Firmware (DevKit V4)

  Hardware:
    ├── LCD 16x2 I2C (0x27)    SDA=21, SCL=22
    ├── Servo 1 (Gerbang Masuk) GPIO 25
    ├── Servo 2 (Gerbang Keluar) GPIO 26
    ├── Touch TP233              GPIO 27 (active HIGH)
    ├── RFID 1 (Slot 1/CAM1)  SS=17, RST=33
    ├── RFID 2 (Slot 2/CAM2)  SS=16, RST=32
    ├── RFID 3 (Exit)         SS=5,  RST=14
    └── SPI shared: SCK=18, MISO=19, MOSI=23

  Alur:
    A. Touch → Servo1 buka 3s → tutup → IDLE
    B. Tap RFID1/RFID2 → POST check-in → LCD "Slot X aktif" → IDLE
    C. (Tidak ada — server/CAM deteksi mobil pergi via WiFi)
    D. RFID3 tap → POST verify → sukses → Servo2 buka 3s + running text → IDLE
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <LiquidCrystal_PCF8574.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include "config.h"

// ============================================================
// OBJECTS
// ============================================================
LiquidCrystal_PCF8574 lcd(LCD_ADDR);

// Multi-RFID array: [0]=Slot1, [1]=Slot2, [2]=Exit
MFRC522 rfid[3] = {
  MFRC522(RFID_SLOT1_SS, RFID_SLOT1_RST),
  MFRC522(RFID_SLOT2_SS, RFID_SLOT2_RST),
  MFRC522(RFID_EXIT_SS,  RFID_EXIT_RST)
};

Servo servoEntry;  // Gerbang Masuk (pin 25)
Servo servoExit;   // Gerbang Keluar (pin 26)

// RFID SS pins array (for shared SPI bus management)
const int rfidSS[3] = { RFID_SLOT1_SS, RFID_SLOT2_SS, RFID_EXIT_SS };

// ============================================================
// STATE MACHINE
// ============================================================
enum State {
  STATE_IDLE,
  STATE_GATE_OPEN,       // Servo1 terbuka, tunggu tutup
  STATE_EXIT_GATE        // Servo2 terbuka, running text
};
State state = STATE_IDLE;

// ============================================================
// SERVO TIMING (non-blocking)
// ============================================================
unsigned long servoEntryOpenTime = 0;
bool servoEntryIsOpen = false;

unsigned long servoExitOpenTime = 0;
bool servoExitIsOpen = false;

// ============================================================
// TOUCH EDGE DETECTION
// ============================================================
bool lastTouchState = false;

// ============================================================
// RUNNING TEXT
// ============================================================
unsigned long lastScrollTime = 0;
String runningTextMsg = "";
bool runningTextActive = false;

// ============================================================
// WIFI
// ============================================================
unsigned long lastWifiReconnect = 0;

// ============================================================
// FORWARD DECLARATIONS
// ============================================================
void connectWiFi();
void maintainWiFi();
void checkTouch();
void checkServoEntry();
void checkServoExit();
void openEntryGate();
void openExitGate();
String scanRFID(int index);
void checkSlotRFID();
void checkExitRFID();
void postCheckIn(String uid, int slot);
void postVerifyExit(String uid);
void lcdShow(String line1, String line2);
void lcdStartRunningText(String msg);
void lcdUpdateRunningText();

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println(F("\n=== STOPBAY v3.0 ==="));

  // LCD
  Wire.begin(21, 22);
  lcd.begin(LCD_COLS, LCD_ROWS);
  lcd.setBacklight(255);
  lcd.clear();
  lcdShow("STOPBAY v3.0", "Initializing...");

  // Touch
  pinMode(TOUCH_PIN, INPUT);

  // SPI + RFID init
  // Set all SS pins HIGH (deselected) before init
  pinMode(RFID_SLOT1_SS, OUTPUT);
  pinMode(RFID_SLOT2_SS, OUTPUT);
  pinMode(RFID_EXIT_SS, OUTPUT);
  digitalWrite(RFID_SLOT1_SS, HIGH);
  digitalWrite(RFID_SLOT2_SS, HIGH);
  digitalWrite(RFID_EXIT_SS, HIGH);

  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI);
  
  // Init each RFID with its SS pin LOW (others HIGH)
  for (int i = 0; i < 3; i++) {
    // Deselect all first
    digitalWrite(RFID_SLOT1_SS, HIGH);
    digitalWrite(RFID_SLOT2_SS, HIGH);
    digitalWrite(RFID_EXIT_SS, HIGH);
    delay(10);
    
    // Select this RFID
    digitalWrite(rfidSS[i], LOW);
    delay(10);
    
    rfid[i].PCD_Init();
    rfid[i].PCD_AntennaOn();  // Enable RF field
    byte v = rfid[i].PCD_ReadRegister(rfid[i].VersionReg);
    Serial.printf("[RFID-%d] v0x%02X (SS=%d)\n", i + 1, v, rfidSS[i]);
    
    // Deselect after init
    digitalWrite(rfidSS[i], HIGH);
    delay(10);
  }

  // Servo
  servoEntry.attach(SERVO_ENTRY_PIN);
  servoExit.attach(SERVO_EXIT_PIN);
  servoEntry.write(SERVO_CLOSE_ANGLE);
  servoExit.write(SERVO_CLOSE_ANGLE);

  // WiFi
  connectWiFi();

  // Ready
  state = STATE_IDLE;
  lcdShow("Tap kartu", "untuk parkir");
  Serial.println(F("[SYS] Ready"));
}

// ============================================================
// LOOP
// ============================================================
void loop() {
  maintainWiFi();

  // Debug: print state every 2s
  static unsigned long lastStatePrint = 0;
  if (millis() - lastStatePrint > 2000) {
    lastStatePrint = millis();
    Serial.printf("[LOOP] State: %d\n", state);
  }

  switch (state) {
    case STATE_IDLE:
      checkTouch();
      checkSlotRFID();
      checkExitRFID();
      break;

    case STATE_GATE_OPEN:
      checkServoEntry();  // Non-blocking: tutup setelah 3s
      break;

    case STATE_EXIT_GATE:
      checkServoExit();    // Non-blocking: tutup setelah 3s
      lcdUpdateRunningText();
      break;
  }
}

// ============================================================
// WIFI
// ============================================================
void connectWiFi() {
  Serial.printf("[WiFi] Connecting to %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts++ < 40) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] OK - %s\n", WiFi.localIP().toString().c_str());
    lcdShow("WiFi Connected", WiFi.localIP().toString());
    delay(1500);
  } else {
    Serial.println(F("\n[WiFi] FAILED"));
    lcdShow("WiFi FAILED", "Offline mode");
    delay(1500);
  }
}

void maintainWiFi() {
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiReconnect > 15000) {
    lastWifiReconnect = millis();
    WiFi.reconnect();
  }
}

// ============================================================
// PHASE A: TOUCH → ENTRY GATE
// ============================================================
void checkTouch() {
  bool touchState = digitalRead(TOUCH_PIN);

  // Debug: print touch state every 500ms
  static unsigned long lastTouchPrint = 0;
  if (millis() - lastTouchPrint > 500) {
    lastTouchPrint = millis();
    Serial.printf("[A] Touch state: %d\n", touchState);
  }

  // Edge detection: LOW→HIGH transition
  if (touchState && !lastTouchState) {
    Serial.println(F("[A] Touch detected → opening entry gate"));
    openEntryGate();
    state = STATE_GATE_OPEN;
  }
  lastTouchState = touchState;
}

void openEntryGate() {
  servoEntry.write(SERVO_OPEN_ANGLE);
  servoEntryOpenTime = millis();
  servoEntryIsOpen = true;
  lcdShow("Gerbang Masuk", "Terbuka...");
}

void checkServoEntry() {
  if (!servoEntryIsOpen) return;
  if (millis() - servoEntryOpenTime >= SERVO_OPEN_DURATION_MS) {
    servoEntry.write(SERVO_CLOSE_ANGLE);
    servoEntryIsOpen = false;
    Serial.println(F("[A] Entry gate closed"));
    state = STATE_IDLE;
    lcdShow("Tap kartu", "untuk parkir");
  }
}

// ============================================================
// PHASE B: SLOT CHECK-IN (RFID1 or RFID2)
// ============================================================
void checkSlotRFID() {
  // Scan RFID1 (index 0) dan RFID2 (index 1)
  for (int i = 0; i < 2; i++) {
    String uid = scanRFID(i);
    if (uid.length() > 0) {
      int slot = i + 1;
      Serial.printf("[B] Slot %d tap: %s\n", slot, uid.c_str());
      lcdShow("Slot " + String(slot) + " aktif", "UID: " + uid.substring(0, 8));
      postCheckIn(uid, slot);
      delay(2000);  // Show slot info
      lcdShow("Tap kartu", "untuk parkir");
      return;
    }
  }
}

// ============================================================
// PHASE D: EXIT GATE (RFID3 → verify → servo2 → running text)
// ============================================================
void checkExitRFID() {
  // Debug: print scanning every 1s
  static unsigned long lastScanPrint = 0;
  if (millis() - lastScanPrint > 1000) {
    lastScanPrint = millis();
    Serial.println(F("[D] Scanning RFID Exit..."));
  }

  String uid = scanRFID(2);  // RFID3 = index 2
  if (uid.length() > 0) {
    Serial.printf("[D] Exit tap: %s\n", uid.c_str());
    lcdShow("Verifikasi...", "Tunggu");
    postVerifyExit(uid);
  }
}

void openExitGate() {
  servoExit.write(SERVO_OPEN_ANGLE);
  servoExitOpenTime = millis();
  servoExitIsOpen = true;
  lcdStartRunningText("Pembayaran berhasil, selamat jalan!");
}

void checkServoExit() {
  if (!servoExitIsOpen) return;
  if (millis() - servoExitOpenTime >= SERVO_OPEN_DURATION_MS) {
    servoExit.write(SERVO_CLOSE_ANGLE);
    servoExitIsOpen = false;
    runningTextActive = false;
    Serial.println(F("[D] Exit gate closed"));
    state = STATE_IDLE;
    lcdShow("Tap kartu", "untuk parkir");
  }
}

// ============================================================
// RFID SCAN (array-based, shared SPI)
// ============================================================
String scanRFID(int index) {
  // Activate only this RFID's SS pin (shared SPI bus)
  for (int i = 0; i < 3; i++) {
    digitalWrite(rfidSS[i], (i == index) ? LOW : HIGH);
  }
  delayMicroseconds(500);  // ponytail: SS settle time

  // Enable antenna (ponytail: skip full re-init to save time)
  rfid[index].PCD_AntennaOn();

  bool cardPresent = rfid[index].PICC_IsNewCardPresent();
  if (!cardPresent) {
    // Debug: print version register to check if RFID is alive
    if (millis() % 5000 < 100) {  // Print every ~5s to avoid spam
      byte v = rfid[index].PCD_ReadRegister(rfid[index].VersionReg);
      Serial.printf("[RFID-%d] No card (v0x%02X, SS=%d)\n", index + 1, v, rfidSS[index]);
    }
    return "";
  }
  
  bool cardRead = rfid[index].PICC_ReadCardSerial();
  if (!cardRead) {
    Serial.printf("[RFID-%d] Card present but read failed\n", index + 1);
    return "";
  }

  String uid = "";
  for (byte i = 0; i < rfid[index].uid.size; i++) {
    if (rfid[index].uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid[index].uid.uidByte[i], HEX);
  }
  uid.toUpperCase();

  rfid[index].PICC_HaltA();
  rfid[index].PCD_StopCrypto1();

  Serial.printf("[RFID-%d] Card read OK: %s\n", index + 1, uid.c_str());
  delay(100);  // Debounce (ponytail: reduced from 300ms)
  return uid;
}

// ============================================================
// HTTP: POST /api/parking/checkin
// ============================================================
void postCheckIn(String uid, int slot) {
  if (WiFi.status() != WL_CONNECTED) {
    lcdShow("Offline", "Check-in gagal");
    return;
  }

  HTTPClient http;
  http.begin(String(API_BASE_URL) + "/api/parking/checkin");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  JsonDocument doc;
  doc["uid"] = uid;
  doc["slot"] = slot;

  String body;
  serializeJson(doc, body);
  Serial.println("[HTTP] POST checkin: " + body);

  int code = http.POST(body);
  if (code > 0) {
    String resp = http.getString();
    Serial.printf("[HTTP] %d: %s\n", code, resp.c_str());

    JsonDocument r;
    if (!deserializeJson(r, resp) && r["success"]) {
      lcdShow("Slot " + String(slot) + " Aktif", "UID: " + uid.substring(0, 8));
    } else {
      lcdShow("Check-in Gagal", "Coba lagi");
      state = STATE_IDLE;
    }
  } else {
    Serial.printf("[HTTP] FAIL: %s\n", http.errorToString(code).c_str());
    lcdShow("Server Error", "Check-in gagal");
    state = STATE_IDLE;
  }
  http.end();
}

// ============================================================
// HTTP: POST /api/parking/verify-exit
// ============================================================
void postVerifyExit(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    lcdShow("Offline", "Verify gagal");
    delay(2000);
    lcdShow("Tap kartu", "untuk parkir");
    return;
  }

  HTTPClient http;
  http.begin(String(API_BASE_URL) + "/api/parking/verify-exit");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  JsonDocument doc;
  doc["uid"] = uid;

  String body;
  serializeJson(doc, body);
  Serial.println("[HTTP] POST verify-exit: " + body);

  int code = http.POST(body);
  if (code > 0) {
    String resp = http.getString();
    Serial.printf("[HTTP] %d: %s\n", code, resp.c_str());

    JsonDocument r;
    if (!deserializeJson(r, resp) && r["success"]) {
      // Sukses → buka gerbang keluar + running text
      state = STATE_EXIT_GATE;
      openExitGate();
    } else {
      lcdShow("Pembayaran", "Gagal");
      delay(2000);
      lcdShow("Tap kartu", "untuk parkir");
    }
  } else {
    Serial.printf("[HTTP] FAIL: %s\n", http.errorToString(code).c_str());
    lcdShow("Server Error", "Coba lagi");
    delay(2000);
    lcdShow("Tap kartu", "untuk parkir");
  }
  http.end();
}

// ============================================================
// LCD HELPERS
// ============================================================
void lcdShow(String line1, String line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1.substring(0, LCD_COLS));
  lcd.setCursor(0, 1);
  lcd.print(line2.substring(0, LCD_COLS));
}

void lcdStartRunningText(String msg) {
  runningTextMsg = msg;
  runningTextActive = true;
  lastScrollTime = millis();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Pembayaran OK!");
  lcd.setCursor(0, 1);
  // Print first 16 chars initially
  lcd.print(runningTextMsg.substring(0, LCD_COLS));
}

void lcdUpdateRunningText() {
  if (!runningTextActive) return;
  if (millis() - lastScrollTime < 300) return;  // Scroll speed: 300ms per shift
  lastScrollTime = millis();

  lcd.scrollDisplayLeft();
}
