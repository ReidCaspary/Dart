#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

// ================================
// CAMERA 1 - Static IP: 192.168.4.20
// ================================
// Starlink WiFi credentials
const char* ssid = "Sharewell Wifi";
const char* password = "sharewell";

// Static IP configuration (update gateway to match your network)
IPAddress staticIP(172, 168, 168, 20);
IPAddress gateway(172, 168, 168, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(172, 168, 168, 1);

// ================================
// AI-Thinker ESP32-CAM Pin Definitions
// ================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define LED_GPIO_NUM       4

// Store IP address for HTML page
String WiFiIP = "";

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

bool flashState = false;

// WiFi reconnection
unsigned long lastWifiCheck = 0;
const unsigned long WIFI_CHECK_INTERVAL = 5000;  // Check every 5 seconds
bool wasConnected = false;

// Stream handler - sends MJPEG stream
static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    char part_buf[64];

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("Camera capture failed");
            res = ESP_FAIL;
            break;
        }

        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }
        if (res == ESP_OK) {
            size_t hlen = snprintf(part_buf, 64, _STREAM_PART, fb->len);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
        }

        esp_camera_fb_return(fb);
        fb = NULL;

        if (res != ESP_OK) {
            break;
        }
    }
    return res;
}

// Single capture handler
static esp_err_t capture_handler(httpd_req_t *req) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Camera capture failed");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_send(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    return ESP_OK;
}

// Index page handler - generates HTML with correct stream URL
static esp_err_t index_handler(httpd_req_t *req) {
    String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>Camera 1 - Dart Delivery System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: white;
        }
        h1 { color: #4CAF50; }
        img {
            max-width: 100%;
            height: auto;
            border: 3px solid #4CAF50;
            border-radius: 10px;
        }
        .controls { margin: 20px 0; }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #45a049; }
        .info { margin-top: 20px; color: #888; }
    </style>
</head>
<body>
    <h1>Camera 1 - Dart Delivery System</h1>
    <div>
        <img src="http://)rawliteral" + WiFiIP + R"rawliteral(:81/stream" id="stream">
    </div>
    <div class="controls">
        <button onclick="toggleFlash()">Toggle Flash</button>
        <button onclick="location.href='/capture'">Capture Photo</button>
    </div>
    <div class="info">
        <p>Stream URL: http://)rawliteral" + WiFiIP + R"rawliteral(:81/stream</p>
    </div>
    <script>
        function toggleFlash() {
            fetch('/flash').then(response => response.text()).then(data => alert(data));
        }
    </script>
</body>
</html>
)rawliteral";

    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, html.c_str(), html.length());
}

// Flash toggle handler
static esp_err_t flash_handler(httpd_req_t *req) {
    flashState = !flashState;
    digitalWrite(LED_GPIO_NUM, flashState);

    const char* response = flashState ? "Flash ON" : "Flash OFF";
    httpd_resp_set_type(req, "text/plain");
    return httpd_resp_send(req, response, strlen(response));
}

void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t camera_httpd = NULL;
    httpd_handle_t stream_httpd = NULL;

    // Main server on port 80
    config.server_port = 80;

    httpd_uri_t index_uri = {
        .uri       = "/",
        .method    = HTTP_GET,
        .handler   = index_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t capture_uri = {
        .uri       = "/capture",
        .method    = HTTP_GET,
        .handler   = capture_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t flash_uri = {
        .uri       = "/flash",
        .method    = HTTP_GET,
        .handler   = flash_handler,
        .user_ctx  = NULL
    };

    Serial.printf("Starting web server on port %d\n", config.server_port);
    if (httpd_start(&camera_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(camera_httpd, &index_uri);
        httpd_register_uri_handler(camera_httpd, &capture_uri);
        httpd_register_uri_handler(camera_httpd, &flash_uri);
    }

    // Stream server on port 81
    config.server_port = 81;
    config.ctrl_port = 32769;

    httpd_uri_t stream_uri = {
        .uri       = "/stream",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };

    Serial.printf("Starting stream server on port %d\n", config.server_port);
    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
    }
}

void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println();
    Serial.println("================================");
    Serial.println("Camera 1 - Dart Delivery System");
    Serial.println("Static IP: 172.168.168.20");
    Serial.println("================================");

    // Setup flash LED
    pinMode(LED_GPIO_NUM, OUTPUT);
    digitalWrite(LED_GPIO_NUM, LOW);

    // Camera configuration
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 12;
    config.fb_count = 1;

    // Adjust settings based on PSRAM availability
    if (psramFound()) {
        Serial.println("PSRAM found!");
        config.frame_size = FRAMESIZE_VGA;  // 640x480 for smooth streaming
        config.jpeg_quality = 10;
        config.fb_count = 2;
        config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
        Serial.println("No PSRAM found.");
        config.frame_size = FRAMESIZE_CIF;  // 400x296
        config.fb_location = CAMERA_FB_IN_DRAM;
    }

    // Initialize camera
    Serial.println("Initializing camera...");
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        return;
    }
    Serial.println("Camera initialized!");

    // Get camera sensor and apply OV3660 specific settings
    sensor_t *s = esp_camera_sensor_get();
    if (s->id.PID == OV3660_PID) {
        Serial.println("OV3660 detected!");
        s->set_vflip(s, 1);
        s->set_brightness(s, 1);
        s->set_saturation(s, -2);
    }

    // Configure static IP
    if (!WiFi.config(staticIP, gateway, subnet, dns)) {
        Serial.println("Static IP configuration failed!");
    }

    // Connect to WiFi
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);
    WiFi.setSleep(false);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\nWiFi connection failed!");
        return;
    }

    wasConnected = true;
    WiFiIP = WiFi.localIP().toString();

    Serial.println("\nWiFi connected!");
    Serial.println();
    Serial.println("================================");
    Serial.println("Camera 1 Ready!");
    Serial.print("IP Address: ");
    Serial.println(WiFiIP);
    Serial.print("Stream URL: http://");
    Serial.print(WiFiIP);
    Serial.println(":81/stream");
    Serial.println("================================");

    // Start web server
    startCameraServer();
}

void checkWiFiConnection() {
    if (WiFi.status() != WL_CONNECTED) {
        if (wasConnected) {
            Serial.println("WiFi connection lost! Reconnecting...");
            wasConnected = false;
        }

        // Configure static IP again
        WiFi.config(staticIP, gateway, subnet, dns);
        WiFi.begin(ssid, password);

        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 10) {
            delay(500);
            Serial.print(".");
            attempts++;
        }

        if (WiFi.status() == WL_CONNECTED) {
            wasConnected = true;
            WiFiIP = WiFi.localIP().toString();
            Serial.println("\nReconnected to WiFi!");
            Serial.print("IP Address: ");
            Serial.println(WiFiIP);
        }
    } else if (!wasConnected) {
        wasConnected = true;
        Serial.println("WiFi connected!");
    }
}

void loop() {
    unsigned long now = millis();

    // Periodic WiFi check
    if (now - lastWifiCheck >= WIFI_CHECK_INTERVAL) {
        lastWifiCheck = now;
        checkWiFiConnection();
    }

    delay(100);
}
