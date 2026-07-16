/*
  STOPBAY v3.0 — ESP32-CAM Cloud Firmware
  Capture JPEG → PlateRecognizer Cloud API → Backend Render
  Board: AI-THINKER ESP32-CAM (OV2640)

  Libraries needed (Arduino Library Manager):
    - esp32-camera by Espressif
    - ArduinoJson by Benoit Blanchon
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"

// ============================================================
// Camera pin mapping (AI-THINKER ESP32-CAM)
// ============================================================
#define PWDN_GPIO_NUM    32
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM    26
#define SIOC_GPIO_NUM    27
#define Y9_GPIO_NUM      35
#define Y8_GPIO_NUM      34
#define Y7_GPIO_NUM      39
#define Y6_GPIO_NUM      36
#define Y5_GPIO_NUM      21
#define Y4_GPIO_NUM      19
#define Y3_GPIO_NUM      18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM   25
#define HREF_GPIO_NUM    23
#define PCLK_GPIO_NUM    22

#define LED_FLASH         4

// ============================================================
// PlateRecognizer API
// ============================================================
#define PLATEREC_URL   "https://api.platerecognizer.com/v1/plate-reader/"

// ============================================================
// Timing
// ============================================================
#define CAPTURE_INTERVAL_MS  3000   // capture every 3 seconds
#define EMPTY_RESET_COUNT    10     // reset after 10 "no plate" captures

// ============================================================
// Global state
// ============================================================
static String lastPostedPlate = "";
static int emptyCount = 0;
static unsigned long lastCapture = 0;

// ============================================================
// Camera init (sama seperti MJPEG firmware)
// ============================================================
void initCamera() {
  camera_config_t config;
  config.ledc_channel  = LEDC_CHANNEL_0;
  config.ledc_timer    = LEDC_TIMER_0;
  config.pin_d0        = Y2_GPIO_NUM;
  config.pin_d1        = Y3_GPIO_NUM;
  config.pin_d2        = Y4_GPIO_NUM;
  config.pin_d3        = Y5_GPIO_NUM;
  config.pin_d4        = Y6_GPIO_NUM;
  config.pin_d5        = Y7_GPIO_NUM;
  config.pin_d6        = Y8_GPIO_NUM;
  config.pin_d7        = Y9_GPIO_NUM;
  config.pin_xclk      = XCLK_GPIO_NUM;
  config.pin_pclk      = PCLK_GPIO_NUM;
  config.pin_vsync     = VSYNC_GPIO_NUM;
  config.pin_href      = HREF_GPIO_NUM;
  config.pin_sscb_sda  = SIOD_GPIO_NUM;
  config.pin_sscb_scl  = SIOC_GPIO_NUM;
  config.pin_pwdn      = PWDN_GPIO_NUM;
  config.pin_reset     = RESET_GPIO_NUM;
  config.xclk_freq_hz  = 10000000;
  config.pixel_format  = PIXFORMAT_JPEG;
  config.frame_size    = FRAMESIZE_QVGA;   // 320x240
  config.jpeg_quality  = 8;                // lower = better
  config.fb_count      = 1;
  config.fb_location   = CAMERA_FB_IN_DRAM;
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAM] Init failed: 0x%x\n", err);
    ESP.restart();
  }

  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, 0);
  s->set_hmirror(s, 0);
  s->set_brightness(s, 1);
  s->set_contrast(s, 1);
  s->set_saturation(s, 0);
  s->set_sharpness(s, 2);    // sharper = better OCR
  s->set_quality(s, 10);

  Serial.println("[CAM] Initialized");
}

// ============================================================
// WiFi connect
// ============================================================
void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);

  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 40) {
    delay(500);
    Serial.print(".");
    tries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.printf("[WiFi] Connected — IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] FAILED — rebooting...");
    ESP.restart();
  }
}

// ============================================================
// Send JPEG to PlateRecognizer → get plate text
// ============================================================
String recognizePlate(uint8_t *jpgBuf, size_t jpgLen) {
  WiFiClientSecure client;
  client.setInsecure();  // ponytail: skip cert validation for ESP32

  HTTPClient http;
  http.begin(client, PLATEREC_URL);

  String auth = "Token ";
  auth += PLATERECOGNIZER_TOKEN;
  http.addHeader("Authorization", auth);

  // Build multipart form body manually
  String boundary = "----STOPBAY";
  String contentType = "multipart/form-data; boundary=" + boundary;
  http.addHeader("Content-Type", contentType);

  // Body start: upload file part
  String bodyStart = "--" + boundary + "\r\n";
  bodyStart += "Content-Disposition: form-data; name=\"upload\"; filename=\"plate.jpg\"\r\n";
  bodyStart += "Content-Type: image/jpeg\r\n\r\n";

  // Body end: regions + closing boundary
  String bodyEnd = "\r\n--" + boundary + "\r\n";
  bodyEnd += "Content-Disposition: form-data; name=\"regions\"\r\n\r\n";
  bodyEnd += "id\r\n";
  bodyEnd += "--" + boundary + "--\r\n";

  size_t totalLen = bodyStart.length() + jpgLen + bodyEnd.length();

  // ESP32 HTTPClient workaround: use sendRequest + write data manually
  // ponytail: allocate on heap, stack too small for JPEG + headers
  uint8_t *bodyBuf = (uint8_t *)malloc(totalLen);
  if (!bodyBuf) {
    Serial.println("[PlateRec] ERROR: malloc failed");
    http.end();
    return "";
  }

  size_t pos = 0;
  memcpy(bodyBuf + pos, bodyStart.c_str(), bodyStart.length());
  pos += bodyStart.length();
  memcpy(bodyBuf + pos, jpgBuf, jpgLen);
  pos += jpgLen;
  memcpy(bodyBuf + pos, bodyEnd.c_str(), bodyEnd.length());

  int code = http.POST(bodyBuf, totalLen);
  free(bodyBuf);

  if (code != 200 && code != 201) {
    Serial.printf("[PlateRec] HTTP %d — %s\n", code, http.getString().c_str());
    http.end();
    return "";
  }

  String response = http.getString();
  http.end();

  // Parse JSON
  StaticJsonDocument<1024> doc;
  DeserializationError err = deserializeJson(doc, response);
  if (err) {
    Serial.printf("[PlateRec] JSON parse error: %s\n", err.c_str());
    return "";
  }

  JsonArray results = doc["results"].as<JsonArray>();
  if (results.size() == 0) {
    Serial.println("[PlateRec] No plate found");
    return "";
  }

  String plate = results[0]["plate"].as<String>();
  float confidence = results[0]["confidence"].as<float>();
  int calls = doc["usage"]["calls"].as<int>();
  int maxCalls = doc["usage"]["max_calls"].as<int>();

  Serial.printf("[PlateRec] %s (confidence: %.1f%%, calls: %d/%d)\n",
                plate.c_str(), confidence, calls, maxCalls);

  if (confidence < 80.0) {
    Serial.printf("[PlateRec] Confidence too low (%.1f%%), skipping\n", confidence);
    return "";
  }

  return plate;
}

// ============================================================
// POST plate to backend
// ============================================================
bool postToBackend(String plate) {
  WiFiClient client;  // plain HTTP or HTTPS depends on BACKEND_URL
  HTTPClient http;

  String url = String(BACKEND_URL) + "/api/parking/space-occupied";
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");

  // Build JSON body
  StaticJsonDocument<256> doc;
  doc["plate_number"]    = plate;
  doc["parking_space_id"] = PARKING_SPACE_ID;
  doc["space_label"]     = SPACE_LABEL;

  String json;
  serializeJson(doc, json);

  int code = http.POST(json);
  String resp = http.getString();
  http.end();

  if (code == 200) {
    Serial.printf("[Backend] POST %s -> %d OK\n", plate.c_str(), code);
    return true;
  } else {
    Serial.printf("[Backend] POST %s -> %d FAIL: %s\n", plate.c_str(), code, resp.c_str());
    return false;
  }
}

// ============================================================
// Setup
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n\nSTOPBAY v3.0 — ESP32-CAM Cloud");
  Serial.println("================================");

  // Flash LED indicator
  ledcSetup(0, 5000, 8);
  ledcAttachPin(LED_FLASH, 0);
  ledcWrite(0, 10);

  initCamera();
  connectWiFi();

  Serial.printf("[Config] Backend: %s\n", BACKEND_URL);
  Serial.printf("[Config] Space: %s (%s)\n", PARKING_SPACE_ID, SPACE_LABEL);
  Serial.printf("[Config] Interval: %dms\n", CAPTURE_INTERVAL_MS);
  Serial.println("================================");
}

// ============================================================
// Loop
// ============================================================
void loop() {
  // Timing
  if (millis() - lastCapture < CAPTURE_INTERVAL_MS) {
    delay(100);
    return;
  }
  lastCapture = millis();

  // WiFi check
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Lost — reconnecting...");
    WiFi.reconnect();
    delay(3000);
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[WiFi] Still lost — rebooting...");
      ESP.restart();
    }
  }

  // Capture frame
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[CAM] Capture failed");
    return;
  }

  if (fb->format != PIXFORMAT_JPEG) {
    esp_camera_fb_return(fb);
    return;
  }

  Serial.printf("[CAM] Captured %d bytes, heap: %d\n", fb->len, ESP.getFreeHeap());

  // Recognize plate
  String plate = recognizePlate(fb->buf, fb->len);
  esp_camera_fb_return(fb);

  if (plate.length() == 0) {
    emptyCount++;
    if (emptyCount >= EMPTY_RESET_COUNT && lastPostedPlate.length() > 0) {
      Serial.println("[State] Plate left — reset");
      lastPostedPlate = "";
      emptyCount = 0;
    }
    return;
  }

  emptyCount = 0;

  // Debounce: only POST if different from last posted
  if (plate != lastPostedPlate) {
    if (postToBackend(plate)) {
      lastPostedPlate = plate;
    }
  } else {
    Serial.printf("[State] Same plate (%s), skip POST\n", plate.c_str());
  }
}
