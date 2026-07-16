/*
  STOPBAY - ESP32-CAM Dummy Plate Sender v2.0
  Simulasi kamera pemindai plat nomor + dummy snapshot.
  Mengirim string dummy plate via Serial (U0T/U0R) ke Main ESP32.

  Wiring to Main ESP32:
    CAM 5V   -> 5V Breadboard
    CAM GND  -> GND Breadboard
    CAM TX/U0T -> GPIO 16 (RX2) Main ESP32
    CAM RX/U0R -> GPIO 17 (TX2) Main ESP32

  POWER NOTE: Power ESP32-CAM from 5V rail (NOT USB) to avoid
  Serial0 conflict with the USB-to-UART chip.
*/

#include "esp_camera.h"

// Dummy plate numbers
const char* plates[] = {
  "B 1234 ABC",
  "B 5678 XYZ",
  "D 9012 EFG",
  "L 3456 HIJ",
  "F 7890 KLM"
};
const int numPlates = sizeof(plates) / sizeof(plates[0]);
int idx = 0;

const unsigned long INTERVAL = 15000;  // 15 detik antar kirim
unsigned long lastSend = 0;

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[STOPBAY-CAM] v2.0 Dummy Plate Sender");
  Serial.println("[STOPBAY-CAM] Interval: 15 detik");

  // Flash LED indikator (GPIO 4)
  pinMode(4, OUTPUT);
  digitalWrite(4, LOW);

  Serial.println("[STOPBAY-CAM] Siap mengirim ke Main ESP32");
}

// ============================================================
// LOOP
// ============================================================
void loop() {
  unsigned long now = millis();

  if (now - lastSend >= INTERVAL) {
    lastSend = now;
    sendPlate();
    idx = (idx + 1) % numPlates;
  }

  // Flash LED 1 detik sebelum kirim
  digitalWrite(4, (now - lastSend > INTERVAL - 1000) ? HIGH : LOW);
  delay(100);
}

// ============================================================
// SEND PLATE
// ============================================================
void sendPlate() {
  const char* plate = plates[idx];

  Serial.printf("[CAM] Sending: %s\n", plate);

  // Kirim plate via Serial ke Main ESP32
  Serial.println(plate);

  // Flash LED
  digitalWrite(4, HIGH);
  delay(80);
  digitalWrite(4, LOW);
}
