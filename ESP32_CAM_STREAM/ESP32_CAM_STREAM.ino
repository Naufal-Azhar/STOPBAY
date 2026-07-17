/*
  STOPBAY v3.0 — ESP32-S/CAM MJPEG Stream Server
  Serve live video di http://<IP>/cam.mjpeg
  Board: AI-THINKER ESP32-CAM (OV2640)
*/

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include <ArduinoOTA.h>

// ============================================================
// WiFi
// ============================================================
const char* ssid     = "Infinix NOTE Edge";
const char* password = "wellwellwell";

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

httpd_handle_t stream_httpd = NULL;

#define PART_BOUNDARY "123456789000000000000987654321"

static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// ============================================================
// MJPEG stream handler
// ============================================================
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t *_jpg_buf = NULL;
  char *part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
      break;
    }

    if (fb->format != PIXFORMAT_JPEG) {
      // JPEG only, skip non-JPEG frames
      esp_camera_fb_return(fb);
      fb = NULL;
      continue;
    }

    _jpg_buf_len = fb->len;
    _jpg_buf = fb->buf;

    if (httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY)) != ESP_OK) {
      esp_camera_fb_return(fb);
      res = ESP_FAIL;
      break;
    }

    size_t hlen = snprintf((char *)part_buf, 64, _STREAM_PART, _jpg_buf_len);
    if (httpd_resp_send_chunk(req, (const char *)part_buf, hlen) != ESP_OK) {
      esp_camera_fb_return(fb);
      res = ESP_FAIL;
      break;
    }
    if (httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len) != ESP_OK) {
      esp_camera_fb_return(fb);
      res = ESP_FAIL;
      break;
    }

    esp_camera_fb_return(fb);
  }

  return res;
}

// ============================================================
// Start camera server
// ============================================================
void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_uri_t stream_uri = {
      .uri       = "/cam.mjpeg",
      .method    = HTTP_GET,
      .handler   = stream_handler,
      .user_ctx  = NULL
    };
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}

// ============================================================
// Camera init
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
  config.xclk_freq_hz  = 10000000;         // 10MHz (stable)
  config.pixel_format  = PIXFORMAT_JPEG;
  config.frame_size    = FRAMESIZE_QVGA;   // 320x240 (readable plates)
  config.jpeg_quality  = 8;                // 0-63, lower=better quality
  config.fb_count      = 1;
  config.fb_location   = CAMERA_FB_IN_DRAM;
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, 0);       // 0 = normal (kalau masih terbalik ganti ke 1)
  s->set_hmirror(s, 0);      // 1 = flip horizontal, 0 = normal
  s->set_brightness(s, 1);   // 0 <-> 2
  s->set_contrast(s, 1);
  s->set_saturation(s, 0);
  s->set_sharpness(s, 2);    // 0-3, higher=sharper edges (text readable)
  s->set_quality(s, 10);     // internal sensor quality
}

// ============================================================
// Setup
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // Camera init
  initCamera();

  // Flash LED — dim indicator (PWM GPIO4, channel 0, 5kHz)
  ledcSetup(0, 5000, 8);
  ledcAttachPin(LED_FLASH, 0);
  ledcWrite(0, 10);  // barely visible

  // WiFi connect
  WiFi.begin(ssid, password);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);

  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Camera stream ready: http://");
  Serial.println(WiFi.localIP());
  Serial.println("/cam.mjpeg");

  // OTA (upload firmware via WiFi, no USB needed)
  ArduinoOTA.setHostname("esp32cam");
  ArduinoOTA.setPassword("admin");
  ArduinoOTA.onStart([]() { Serial.println("[OTA] Start"); });
  ArduinoOTA.onEnd([]() { Serial.println("[OTA] Done"); });
  ArduinoOTA.onError([](ota_error_t e) { Serial.printf("[OTA] Error %u\n", e); });
  ArduinoOTA.begin();
  Serial.println("[OTA] Ready");

  // Start stream server
  startCameraServer();
}

void loop() {
  ArduinoOTA.handle();

  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 30000) {
    lastCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[WATCHDOG] WiFi lost — rebooting...");
      ESP.restart();
    }
    Serial.printf("[WATCHDOG] Alive — heap: %d\n", ESP.getFreeHeap());
  }
  delay(1000);
}
