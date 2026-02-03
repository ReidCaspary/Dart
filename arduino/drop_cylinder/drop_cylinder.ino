/**
 * Drop Cylinder Controller - ESP32 Sketch
 *
 * Controls a Reef's 800is servo winch via PWM for lowering/raising a drop cylinder.
 * Communicates over WiFi with the Python GUI.
 *
 * Hardware:
 * - Arduino Nano ESP32
 * - Reef's 800is Servo Winch (PWM controlled)
 *
 * PWM Control:
 * - 1.0ms pulse = Full speed CCW
 * - 1.5ms pulse = Stop
 * - 2.0ms pulse = Full speed CW
 * - 50 Hz frequency
 *
 * WiFi:
 * - Creates AP "DropCylinder" for configuration
 * - Can connect to existing network (Station mode)
 * - Runs TCP server on port 8080
 */

#include <WiFi.h>
#include <WiFiAP.h>
#include <Preferences.h>

// ============================================================================
// Pin Definitions
// ============================================================================

const int SERVO_PIN = D2;  // PWM output to servo

// ============================================================================
// PWM Configuration (Reef's 800is servo)
// ============================================================================

const int LEDC_RES = 14;           // 14-bit resolution
const int SERVO_HZ = 50;           // 50 Hz (20ms period)
const int PWM_MIN_US = 1000;       // 1.0ms = full CCW
const int PWM_STOP_US = 1500;      // 1.5ms = stop
const int PWM_MAX_US = 2000;       // 2.0ms = full CW

// Trim adjustment (tweak if servo creeps at "stop")
int trimOffsetUs = 0;              // Adjustable via command

// Speed scaling (0.0 to 1.0)
float jogSpeed = 0.5f;             // 50% speed for jogging

// ============================================================================
// WiFi Configuration
// ============================================================================

// Starlink WiFi credentials
const char* DEFAULT_SSID = "Sharewell Wifi";
const char* DEFAULT_PASS = "sharewell";

// Static IP configuration (update gateway to match your network)
IPAddress staticIP(172, 168, 168, 10);
IPAddress gateway(172, 168, 168, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(172, 168, 168, 1);

// AP mode settings (fallback for configuration/discovery)
const char* AP_SSID = "DartCylinder";
const char* AP_PASS = "dartcyl123";  // Min 8 chars

// Station mode settings (stored in preferences)
Preferences preferences;
String staSsid = "";
String staPass = "";
bool stationMode = false;

// WiFi reconnection
unsigned long lastWifiCheck = 0;
const unsigned long WIFI_CHECK_INTERVAL = 5000;  // Check every 5 seconds
bool wasConnected = false;

// TCP Server
WiFiServer server(8080);
WiFiClient client;

// ============================================================================
// State Variables
// ============================================================================

enum CylinderMode : uint8_t {
  MODE_IDLE,
  MODE_JOG_DOWN,
  MODE_JOG_UP,
  MODE_MOVE_TO_START,
  MODE_MOVE_TO_STOP
};

CylinderMode currentMode = MODE_IDLE;

// Position tracking (time-based, in milliseconds of travel)
int32_t currentPositionMs = 0;     // Current position estimate
int32_t startPositionMs = 0;       // Saved "start" (up) position
int32_t stopPositionMs = 5000;     // Saved "stop" (down) position - default 5 seconds
bool startSaved = false;
bool stopSaved = false;

// Motion timing
uint32_t motionStartTime = 0;
int32_t motionTargetMs = 0;

// ============================================================================
// Command Buffer
// ============================================================================

const int CMD_BUFFER_SIZE = 64;
char cmdBuffer[CMD_BUFFER_SIZE];
int cmdBufferIndex = 0;

// ============================================================================
// PWM Helper Functions
// ============================================================================

static inline uint32_t usToDuty(int us) {
  const uint32_t maxDuty = (1UL << LEDC_RES) - 1;
  const uint32_t periodUs = 1000000UL / SERVO_HZ;
  uint64_t duty = (uint64_t)us * maxDuty / periodUs;
  if (duty > maxDuty) duty = maxDuty;
  return (uint32_t)duty;
}

void servoWriteUs(int us) {
  ledcWrite(SERVO_PIN, usToDuty(us));
}

// ============================================================================
// Setup
// ============================================================================

void setup() {
  Serial.begin(115200);
  Serial.println("Drop Cylinder Controller Starting...");
  Serial.print("Servo pin D2 = GPIO ");
  Serial.println(SERVO_PIN);

  // Initialize LEDC PWM for servo
  bool ok = ledcAttach(SERVO_PIN, SERVO_HZ, LEDC_RES);
  Serial.print("ledcAttach: ");
  Serial.println(ok ? "SUCCESS" : "FAILED");

  setServoStop();

  // Load saved WiFi credentials
  preferences.begin("dropcyl", false);
  staSsid = preferences.getString("ssid", DEFAULT_SSID);
  staPass = preferences.getString("pass", DEFAULT_PASS);
  trimOffsetUs = preferences.getInt("trim", 0);
  startPositionMs = preferences.getInt("startPos", 0);
  stopPositionMs = preferences.getInt("stopPos", 5000);
  startSaved = preferences.getBool("startSaved", false);
  stopSaved = preferences.getBool("stopSaved", false);

  // Configure static IP
  if (!WiFi.config(staticIP, gateway, subnet, dns)) {
    Serial.println("Static IP configuration failed!");
  }

  // Try to connect to network (default or saved)
  Serial.print("Connecting to WiFi: ");
  Serial.println(staSsid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(staSsid.c_str(), staPass.c_str());

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    stationMode = true;
    wasConnected = true;
    Serial.println("\nConnected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect, starting AP mode");
    startAPMode();
  }

  // Start TCP server
  server.begin();
  Serial.println("TCP Server started on port 8080");
}

void startAPMode() {
  stationMode = false;
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  Serial.print("AP Mode - SSID: ");
  Serial.println(AP_SSID);
  Serial.print("AP IP Address: ");
  Serial.println(WiFi.softAPIP());
}

// ============================================================================
// WiFi Reconnection
// ============================================================================

void checkWiFiConnection() {
  if (!stationMode) return;  // Don't check if in AP mode

  if (WiFi.status() != WL_CONNECTED) {
    if (wasConnected) {
      Serial.println("WiFi connection lost! Reconnecting...");
      wasConnected = false;
    }

    // Configure static IP again
    WiFi.config(staticIP, gateway, subnet, dns);
    WiFi.begin(staSsid.c_str(), staPass.c_str());

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 10) {
      delay(500);
      Serial.print(".");
      attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      wasConnected = true;
      Serial.println("\nReconnected to WiFi!");
      Serial.print("IP Address: ");
      Serial.println(WiFi.localIP());
    }
  } else if (!wasConnected) {
    wasConnected = true;
  }
}

// ============================================================================
// Main Loop
// ============================================================================

void loop() {
  unsigned long now = millis();

  // Periodic WiFi check (only in station mode)
  if (now - lastWifiCheck >= WIFI_CHECK_INTERVAL) {
    lastWifiCheck = now;
    checkWiFiConnection();
  }

  // Handle WiFi client
  handleClient();

  // Update motion
  updateMotion();

  // Small delay to prevent watchdog issues
  delay(1);
}

// ============================================================================
// WiFi Client Handling
// ============================================================================

void handleClient() {
  // Check for new client
  if (!client || !client.connected()) {
    client = server.available();
    if (client) {
      Serial.println("Client connected");
      cmdBufferIndex = 0;
    }
  }

  // Read from client
  if (client && client.connected()) {
    while (client.available()) {
      char c = client.read();

      if (c == '\n' || c == '\r') {
        if (cmdBufferIndex > 0) {
          cmdBuffer[cmdBufferIndex] = '\0';
          processCommand(cmdBuffer);
          cmdBufferIndex = 0;
        }
      } else if (cmdBufferIndex < CMD_BUFFER_SIZE - 1) {
        cmdBuffer[cmdBufferIndex++] = c;
      }
    }
  }
}

// ============================================================================
// Command Processing
// ============================================================================

void processCommand(const char* cmd) {
  Serial.print("CMD: ");
  Serial.println(cmd);

  // Status query
  if (strcmp(cmd, "?") == 0) {
    sendStatus();
    return;
  }

  // Jog down (lower cylinder)
  if (strcmp(cmd, "JD") == 0) {
    startJogDown();
    return;
  }

  // Jog up (raise cylinder)
  if (strcmp(cmd, "JU") == 0) {
    startJogUp();
    return;
  }

  // Stop jogging
  if (strcmp(cmd, "JS") == 0) {
    stopMotion();
    return;
  }

  // Go to start position (up)
  if (strcmp(cmd, "GS") == 0) {
    if (startSaved) {
      goToPosition(startPositionMs);
    }
    return;
  }

  // Go to stop position (down)
  if (strcmp(cmd, "GP") == 0) {
    if (stopSaved) {
      goToPosition(stopPositionMs);
    }
    return;
  }

  // Save current as start position
  if (strcmp(cmd, "SS") == 0) {
    startPositionMs = currentPositionMs;
    startSaved = true;
    preferences.putInt("startPos", startPositionMs);
    preferences.putBool("startSaved", true);
    return;
  }

  // Save current as stop position
  if (strcmp(cmd, "SP") == 0) {
    stopPositionMs = currentPositionMs;
    stopSaved = true;
    preferences.putInt("stopPos", stopPositionMs);
    preferences.putBool("stopSaved", true);
    return;
  }

  // Stop all motion
  if (strcmp(cmd, "ST") == 0) {
    stopMotion();
    return;
  }

  // Set trim: TR<offset>  (e.g., TR10, TR-5)
  if (strncmp(cmd, "TR", 2) == 0) {
    trimOffsetUs = atoi(cmd + 2);
    preferences.putInt("trim", trimOffsetUs);
    if (currentMode == MODE_IDLE) {
      setServoStop();  // Apply new trim immediately
    }
    return;
  }

  // Set WiFi credentials: WIFI:<ssid>:<password>
  if (strncmp(cmd, "WIFI:", 5) == 0) {
    String params = String(cmd + 5);
    int colonPos = params.indexOf(':');
    if (colonPos > 0) {
      staSsid = params.substring(0, colonPos);
      staPass = params.substring(colonPos + 1);
      preferences.putString("ssid", staSsid);
      preferences.putString("pass", staPass);
      sendResponse("OK:WIFI_SAVED");
      // Restart to apply
      delay(1000);
      ESP.restart();
    }
    return;
  }

  // Clear WiFi credentials (return to AP mode)
  if (strcmp(cmd, "WIFI_CLEAR") == 0) {
    preferences.putString("ssid", "");
    preferences.putString("pass", "");
    sendResponse("OK:WIFI_CLEARED");
    delay(1000);
    ESP.restart();
    return;
  }

  // Zero position
  if (strcmp(cmd, "ZERO") == 0) {
    currentPositionMs = 0;
    return;
  }

  // Set jog speed: VS<speed 0-100>
  if (strncmp(cmd, "VS", 2) == 0) {
    int speed = atoi(cmd + 2);
    if (speed >= 10 && speed <= 100) {
      jogSpeed = speed / 100.0f;
    }
    return;
  }
}

void sendStatus() {
  if (!client || !client.connected()) return;

  // Format: POS:<ms> MODE:<mode> START:<Y@ms|N> STOP:<Y@ms|N> TRIM:<us> WIFI:<AP|STA> IP:<ip>
  String status = "POS:";
  status += currentPositionMs;
  status += " MODE:";

  switch (currentMode) {
    case MODE_IDLE: status += "IDLE"; break;
    case MODE_JOG_DOWN: status += "JOG_DOWN"; break;
    case MODE_JOG_UP: status += "JOG_UP"; break;
    case MODE_MOVE_TO_START: status += "MOVE_START"; break;
    case MODE_MOVE_TO_STOP: status += "MOVE_STOP"; break;
  }

  status += " START:";
  if (startSaved) {
    status += "Y@";
    status += startPositionMs;
  } else {
    status += "N";
  }

  status += " STOP:";
  if (stopSaved) {
    status += "Y@";
    status += stopPositionMs;
  } else {
    status += "N";
  }

  status += " TRIM:";
  status += trimOffsetUs;

  status += " WIFI:";
  status += stationMode ? "STA" : "AP";

  status += " IP:";
  status += stationMode ? WiFi.localIP().toString() : WiFi.softAPIP().toString();

  status += " SPEED:";
  status += (int)(jogSpeed * 100);

  client.println(status);
}

void sendResponse(const char* msg) {
  if (client && client.connected()) {
    client.println(msg);
  }
}

// ============================================================================
// Servo Control
// ============================================================================

void setServoStop() {
  servoWriteUs(PWM_STOP_US + trimOffsetUs);
}

void setServoDown(float speed) {
  // Down = CW = higher pulse width
  int us = PWM_STOP_US + (int)((PWM_MAX_US - PWM_STOP_US) * speed) + trimOffsetUs;
  servoWriteUs(us);
}

void setServoUp(float speed) {
  // Up = CCW = lower pulse width
  int us = PWM_STOP_US - (int)((PWM_STOP_US - PWM_MIN_US) * speed) + trimOffsetUs;
  servoWriteUs(us);
}

// ============================================================================
// Motion Control
// ============================================================================

void startJogDown() {
  currentMode = MODE_JOG_DOWN;
  motionStartTime = millis();
  setServoDown(jogSpeed);
}

void startJogUp() {
  currentMode = MODE_JOG_UP;
  motionStartTime = millis();
  setServoUp(jogSpeed);
}

void goToPosition(int32_t targetMs) {
  motionTargetMs = targetMs;
  motionStartTime = millis();

  if (targetMs > currentPositionMs) {
    currentMode = MODE_MOVE_TO_STOP;
    setServoDown(jogSpeed);
  } else if (targetMs < currentPositionMs) {
    currentMode = MODE_MOVE_TO_START;
    setServoUp(jogSpeed);
  } else {
    currentMode = MODE_IDLE;
    setServoStop();
  }
}

void stopMotion() {
  currentMode = MODE_IDLE;
  setServoStop();
}

void updateMotion() {
  if (currentMode == MODE_IDLE) {
    return;
  }

  uint32_t now = millis();
  uint32_t elapsed = now - motionStartTime;
  motionStartTime = now;

  // Update position estimate based on direction
  if (currentMode == MODE_JOG_DOWN || currentMode == MODE_MOVE_TO_STOP) {
    currentPositionMs += elapsed;
  } else if (currentMode == MODE_JOG_UP || currentMode == MODE_MOVE_TO_START) {
    currentPositionMs -= elapsed;
    if (currentPositionMs < 0) currentPositionMs = 0;
  }

  // Check if we've reached target for auto-moves
  if (currentMode == MODE_MOVE_TO_STOP && currentPositionMs >= motionTargetMs) {
    currentPositionMs = motionTargetMs;
    stopMotion();
  } else if (currentMode == MODE_MOVE_TO_START && currentPositionMs <= motionTargetMs) {
    currentPositionMs = motionTargetMs;
    stopMotion();
  }
}
