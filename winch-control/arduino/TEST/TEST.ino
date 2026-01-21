// Arduino Nano ESP32 - Continuous rotation servo via LEDC

const int SERVO_PIN = D2;   // Try D2 instead
const int LEDC_RES  = 14;   // Lower resolution
const int SERVO_HZ  = 50;

const int PULSE_CCW  = 1000;
const int PULSE_STOP = 1500;
const int PULSE_CW   = 2000;

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

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  Serial.println("Starting servo test...");
  Serial.print("SERVO_PIN (D2) = GPIO ");
  Serial.println(SERVO_PIN);

  bool ok = ledcAttach(SERVO_PIN, SERVO_HZ, LEDC_RES);
  Serial.print("ledcAttach: ");
  Serial.println(ok ? "SUCCESS" : "FAILED");

  servoWriteUs(PULSE_STOP);
  Serial.println("Set to STOP");
}

void loop() {
  Serial.println("CW");
  servoWriteUs(PULSE_CW);
  delay(3000);

  Serial.println("STOP");
  servoWriteUs(PULSE_STOP);
  delay(2000);

  Serial.println("CCW");
  servoWriteUs(PULSE_CCW);
  delay(3000);

  Serial.println("STOP");
  servoWriteUs(PULSE_STOP);
  delay(2000);
}
