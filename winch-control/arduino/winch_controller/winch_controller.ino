#include <Arduino.h>


// ================= PIN MAP (LOCKED) =================

// INPUTS (pull-up, active LOW)

#define PIN_JOG_L   2   //25

#define PIN_JOG_R   3    //26a

#define PIN_WELL    4  //27

#define PIN_HOME    5  //28

#define PIN_ESTOP   6  // NC sense: LOW=OK, HIGH=ESTOP (INPUT_PULLUP + NC to GND)29


// OUTPUTS to STAC5

#define PIN_STEP    8

#define PIN_DIR     9

#define PIN_ENA     10


// ================= DRIVE / MOTOR SETTINGS =================

static const bool ENA_ACTIVE_LOW = false;

static const bool DIR_INVERT     = false;

static const uint32_t STEP_PULSE_US = 5;


// ================= APPROVED BASE SETTINGS =================

static const float STEPS_PER_REV     = 4000.0f;


static const float MIN_STEP_RPS      = 0.02f;

static const float START_RPS         = 0.10f;


static const float DEFAULT_MAX_RPS_JOG  = 10.0f;

static const float DEFAULT_MAX_RPS_MOVE = 0.75f * DEFAULT_MAX_RPS_JOG;

static float maxRpsJog  = DEFAULT_MAX_RPS_JOG;

static float maxRpsMove = DEFAULT_MAX_RPS_MOVE;


static const float ACCEL_RPS2        = 3.80f;

static const float DECEL_RPS2        = 8.50f;

static const float ACCEL_SOFT_RPS2   = 2.20f;


static const uint32_t SOFTSTART_MS   = 350;


static const uint32_t ENA_SETTLE_MS  = 80;

static const uint32_t JOG_BRAKE_RELEASE_MS = 250;


static const uint32_t DEBOUNCE_MS    = 25;

static const uint32_t LONG_PRESS_MS  = 1200;


// Debug (OFF by default)

static const bool DEBUG_PRINTS = false;

static const uint32_t PRINT_MIN_MS = 200;


// ================= DERIVED =================

static inline float rps_to_sps(float rps)    { return rps * STEPS_PER_REV; }

static inline float rps2_to_sps2(float rps2) { return rps2 * STEPS_PER_REV; }


static const float MIN_STEP_SPS = rps_to_sps(MIN_STEP_RPS);

static const float START_SPS    = rps_to_sps(START_RPS);


static inline float maxSpsJog()  { return rps_to_sps(maxRpsJog); }

static inline float maxSpsMove() { return rps_to_sps(maxRpsMove); }


static inline float accel_sps2()     { return rps2_to_sps2(ACCEL_RPS2); }

static inline float decel_sps2()     { return rps2_to_sps2(DECEL_RPS2); }

static inline float accelSoft_sps2() { return rps2_to_sps2(ACCEL_SOFT_RPS2); }


// ================= STATE =================

enum MotionMode : uint8_t { MODE_IDLE, MODE_JOG, MODE_MOVE };

static MotionMode mode = MODE_IDLE;


static float currentSps = 0.0f;

static uint32_t lastUpdateUs = 0;

static uint32_t nextStepAtUs = 0;

static uint32_t motionStartMs = 0;


static int8_t stepDir = +1;          // +1 / -1

static int64_t posSteps = 0;


static int64_t targetSteps = 0;      // active move target

static int64_t commandedTargetSteps = 0; // last commanded target (for retargeting)


static bool reversing = false;       // true while we decel to flip direction

static int8_t pendingDir = +1;


// Saved points

static int64_t homeSteps = 0, wellSteps = 0;

static bool homeSaved = false, wellSaved = false;


// ================= INPUT / BUTTON EDGE LOGIC =================

static bool homeStable=false, wellStable=false;

static bool homeLastStable=false, wellLastStable=false;

static uint32_t homeLastChangeMs=0, wellLastChangeMs=0;

static uint32_t homePressStartMs=0, wellPressStartMs=0;

static bool homeLong=false, wellLong=false;


static bool homeReleaseEvent=false, wellReleaseEvent=false;

static bool homeWasLong=false, wellWasLong=false;


// ================= SERIAL CONTROL (added for GUI) =================

static bool serialJogLeft = false;

static bool serialJogRight = false;

static const int CMD_BUFFER_SIZE = 32;

static char serialBuffer[CMD_BUFFER_SIZE];

static int serialBufferIndex = 0;


static inline bool pressed(uint8_t pin) { return digitalRead(pin) == LOW; }


static void setEnable(bool en) {

  if (ENA_ACTIVE_LOW) digitalWrite(PIN_ENA, en ? LOW : HIGH);

  else                digitalWrite(PIN_ENA, en ? HIGH : LOW);

}


static void applyDir(int8_t dir) {

  stepDir = (dir >= 0) ? +1 : -1;

  bool level = (stepDir > 0) ? HIGH : LOW;

  if (DIR_INVERT) level = !level;

  digitalWrite(PIN_DIR, level);

}


static void stepPulse() {

  digitalWrite(PIN_STEP, HIGH);

  delayMicroseconds(STEP_PULSE_US);

  digitalWrite(PIN_STEP, LOW);

  posSteps += (stepDir > 0) ? 1 : -1;

}


// Debounced edge events on release:

// - long hold then release => SAVE

// - tap then release => GO

static void updateButtons(bool hRaw, bool wRaw) {

  homeReleaseEvent = wellReleaseEvent = false;

  homeWasLong = wellWasLong = false;


  uint32_t now = millis();


  // HOME

  if (hRaw != homeStable) {

    if (now - homeLastChangeMs >= DEBOUNCE_MS) {

      homeLastStable = homeStable;

      homeStable = hRaw;

      homeLastChangeMs = now;


      if (homeStable && !homeLastStable) { homePressStartMs = now; homeLong = false; }

      if (!homeStable && homeLastStable) { homeReleaseEvent = true; homeWasLong = homeLong; }

    }

  }

  if (homeStable && !homeLong && (now - homePressStartMs >= LONG_PRESS_MS)) homeLong = true;


  // WELL

  if (wRaw != wellStable) {

    if (now - wellLastChangeMs >= DEBOUNCE_MS) {

      wellLastStable = wellStable;

      wellStable = wRaw;

      wellLastChangeMs = now;


      if (wellStable && !wellLastStable) { wellPressStartMs = now; wellLong = false; }

      if (!wellStable && wellLastStable) { wellReleaseEvent = true; wellWasLong = wellLong; }

    }

  }

  if (wellStable && !wellLong && (now - wellPressStartMs >= LONG_PRESS_MS)) wellLong = true;

}


// ================= MOTION HELPERS =================

static float currentAccel() {

  uint32_t t = millis() - motionStartMs;

  return (t < SOFTSTART_MS) ? accelSoft_sps2() : accel_sps2();

}


static float stoppingDistSteps(float v_sps) {

  float a = decel_sps2();

  if (a < 1.0f) a = 1.0f;

  return (v_sps * v_sps) / (2.0f * a);

}


// Smooth takeover: cancel MOVE ownership, keep speed, prevent backlog burst

static void cancelMoveForJogTakeover(uint32_t nowUs) {

  if (mode == MODE_MOVE) {

    mode = MODE_IDLE;

    reversing = false;

    targetSteps = posSteps;

    commandedTargetSteps = posSteps;

    nextStepAtUs = nowUs; // reset scheduler to "now" to avoid bursts

  }

}


// Retarget MOVE:

// - if already moving and direction changes, decel to near stop then flip exactly once

// - keep speed otherwise; do NOT restart softstart window on retarget

static void commandMoveTo(int64_t newTarget, uint32_t nowUs) {

  commandedTargetSteps = newTarget;


  // If we were idle (or jog just ended), start a move cleanly

  if (mode != MODE_MOVE) {

    targetSteps = newTarget;

    int64_t rem = targetSteps - posSteps;

    if (rem == 0) { mode = MODE_IDLE; currentSps = 0.0f; reversing = false; return; }

    applyDir((rem > 0) ? +1 : -1);

    if (currentSps < START_SPS) currentSps = START_SPS;

    mode = MODE_MOVE;

    reversing = false;

    motionStartMs = millis();

    nextStepAtUs = nowUs; // avoid backlog

    return;

  }


  // Already in MOVE: retarget

  targetSteps = newTarget;

  int64_t rem = targetSteps - posSteps;

  if (rem == 0) { mode = MODE_IDLE; currentSps = 0.0f; reversing = false; return; }


  int8_t wantDir = (rem > 0) ? +1 : -1;


  // If we need to reverse, do it safely: decel first, then flip once

  if (wantDir != stepDir) {

    pendingDir = wantDir;

    reversing = true;

  } else {

    reversing = false;

    // keep going; scheduler stays stable

  }


  // IMPORTANT: do not touch motionStartMs here (keeps smoothness)

  (void)nowUs;

}


// ================= SERIAL COMMUNICATION =================

static void processSerialCommand(const char* cmd, uint32_t nowUs) {


  // Jog commands

  if (strcmp(cmd, "JL") == 0) {

    serialJogLeft = true;

    serialJogRight = false;

    return;

  }


  if (strcmp(cmd, "JR") == 0) {

    serialJogRight = true;

    serialJogLeft = false;

    return;

  }


  if (strcmp(cmd, "JS") == 0) {

    serialJogLeft = false;

    serialJogRight = false;

    return;

  }


  // Go to saved positions

  if (strcmp(cmd, "GH") == 0) {

    if (homeSaved) {

      commandMoveTo(homeSteps, nowUs);

    }

    return;

  }


  if (strcmp(cmd, "GW") == 0) {

    if (wellSaved) {

      commandMoveTo(wellSteps, nowUs);

    }

    return;

  }


  // Save positions

  if (strcmp(cmd, "SH") == 0) {

    homeSteps = posSteps;

    homeSaved = true;

    return;

  }


  if (strcmp(cmd, "SW") == 0) {

    wellSteps = posSteps;

    wellSaved = true;

    return;

  }


  // Stop

  if (strcmp(cmd, "ST") == 0) {

    serialJogLeft = false;

    serialJogRight = false;

    if (mode == MODE_MOVE) {

      targetSteps = posSteps;

      commandedTargetSteps = posSteps;

    }

    return;

  }


  // Go to absolute position: GT<steps>

  if (strncmp(cmd, "GT", 2) == 0) {

    long pos = atol(cmd + 2);

    commandMoveTo(pos, nowUs);

    return;

  }


  // Move relative: MR<steps>

  if (strncmp(cmd, "MR", 2) == 0) {

    long delta = atol(cmd + 2);

    commandMoveTo(posSteps + delta, nowUs);

    return;

  }


  // Set jog speed: VJ<rps>

  if (strncmp(cmd, "VJ", 2) == 0) {

    float rps = atof(cmd + 2);

    if (rps >= 0.1f && rps <= 20.0f) {

      maxRpsJog = rps;

    }

    return;

  }


  // Set move speed: VM<rps>

  if (strncmp(cmd, "VM", 2) == 0) {

    float rps = atof(cmd + 2);

    if (rps >= 0.1f && rps <= 20.0f) {

      maxRpsMove = rps;

    }

    return;

  }

}


static void processSerial(uint32_t nowUs) {

  while (Serial.available() > 0) {

    char c = Serial.read();


    if (c == '\n' || c == '\r') {

      if (serialBufferIndex > 0) {

        serialBuffer[serialBufferIndex] = '\0';

        processSerialCommand(serialBuffer, nowUs);

        serialBufferIndex = 0;

      }

    } else if (serialBufferIndex < CMD_BUFFER_SIZE - 1) {

      serialBuffer[serialBufferIndex++] = c;

    }

  }

}


// ================= SETUP / LOOP =================

void setup() {

  Serial.begin(115200);


  pinMode(PIN_JOG_L, INPUT_PULLUP);

  pinMode(PIN_JOG_R, INPUT_PULLUP);

  pinMode(PIN_HOME,  INPUT_PULLUP);

  pinMode(PIN_WELL,  INPUT_PULLUP);

  pinMode(PIN_ESTOP, INPUT_PULLUP);


  pinMode(PIN_STEP, OUTPUT);

  pinMode(PIN_DIR,  OUTPUT);

  pinMode(PIN_ENA,  OUTPUT);


  digitalWrite(PIN_STEP, LOW);

  digitalWrite(PIN_DIR,  LOW);

  setEnable(false);


  lastUpdateUs = micros();

  nextStepAtUs = micros();

}


void loop() {

  const bool jl = pressed(PIN_JOG_L);

  const bool jr = pressed(PIN_JOG_R);

  const bool hRaw = pressed(PIN_HOME);

  const bool wRaw = pressed(PIN_WELL);


  // NC chain: LOW=OK, HIGH=ESTOP

  const bool eStopActive = (digitalRead(PIN_ESTOP) == HIGH);


  // ESTOP: hard stop (and stop generating steps)

  if (eStopActive) {

    setEnable(false);

    mode = MODE_IDLE;

    reversing = false;

    currentSps = 0.0f;

    serialJogLeft = false;

    serialJogRight = false;

    delay(20);

    return;

  }


  // Enable + settle

  static bool enaOn = false;

  static uint32_t enaOnMs = 0;

  setEnable(true);

  if (!enaOn) { enaOn = true; enaOnMs = millis(); }

  if (millis() - enaOnMs < ENA_SETTLE_MS) return;


  // Get time for serial commands

  const uint32_t nowUs = micros();


  // Process serial commands

  processSerial(nowUs);


  // Update buttons (edge detection)

  updateButtons(hRaw, wRaw);


  // ---------- BUTTON COMMANDS (tap=GO, long=SAVE) ----------


  if (homeReleaseEvent) {

    if (homeWasLong) { homeSteps = posSteps; homeSaved = true; }

    else if (homeSaved) { commandMoveTo(homeSteps, nowUs); }

  }

  if (wellReleaseEvent) {

    if (wellWasLong) { wellSteps = posSteps; wellSaved = true; }

    else if (wellSaved) { commandMoveTo(wellSteps, nowUs); }

  }


  // ---------- JOG OVERRIDE ----------

  // Combine physical and serial jog inputs

  const bool jogL = jl || serialJogLeft;

  const bool jogR = jr || serialJogRight;


  int8_t demandDir = 0;

  if (jogL && !jogR) demandDir = -1;

  else if (jogR && !jogL) demandDir = +1;


  static bool jogStartPending = false;

  static uint32_t jogPendingMs = 0;


  if (demandDir != 0) {

    // jog takes ownership immediately

    cancelMoveForJogTakeover(nowUs);


    applyDir(demandDir);


    if (mode != MODE_JOG && currentSps <= 0.0f) {

      mode = MODE_JOG;

      motionStartMs = millis();

      jogStartPending = true;

      jogPendingMs = millis();

      currentSps = 0.0f;

    } else {

      mode = MODE_JOG;

      if (currentSps < START_SPS) currentSps = START_SPS;

      motionStartMs = millis();

      jogStartPending = false;

    }

  } else {

    jogStartPending = false;

    if (mode == MODE_JOG) mode = MODE_IDLE;

  }


  // Jog brake-release delay (from stop)

  if (jogStartPending) {

    if (millis() - jogPendingMs >= JOG_BRAKE_RELEASE_MS) {

      jogStartPending = false;

      currentSps = MIN_STEP_SPS;

      motionStartMs = millis();

      nextStepAtUs = nowUs;

    } else {

      return; // hold still during brake release window

    }

  }


  // ---------- TIMEBASE ----------

  const uint32_t tUs = micros();

  const float dt = (tUs - lastUpdateUs) / 1000000.0f;

  lastUpdateUs = tUs;


  // ---------- SPEED / MODE UPDATE ----------

  if (mode == MODE_IDLE) {

    if (currentSps > 0.0f) {

      currentSps -= decel_sps2() * dt;

      if (currentSps < 0.0f) currentSps = 0.0f;

    }

  } else if (mode == MODE_JOG) {

    currentSps += currentAccel() * dt;

    if (currentSps > maxSpsJog()) currentSps = maxSpsJog();

    if (currentSps < MIN_STEP_SPS) currentSps = MIN_STEP_SPS;

  } else { // MODE_MOVE

    int64_t rem = targetSteps - posSteps;


    if (rem == 0) {

      mode = MODE_IDLE;

      reversing = false;

    } else {

      const float distAbs = (float) llabs(rem);


      // If reversal requested: decel to near stop, then flip ONCE

      if (reversing) {

        currentSps -= decel_sps2() * dt;

        if (currentSps < START_SPS) {

          currentSps = START_SPS;

          applyDir(pendingDir);

          reversing = false;

          nextStepAtUs = tUs; // prevent backlog burst when flipping

        }

      } else {

        // normal move accel/decel profile

        const float stopDist = stoppingDistSteps(currentSps);


        if (distAbs <= stopDist + 1.0f) {

          currentSps -= decel_sps2() * dt;

          if (currentSps < MIN_STEP_SPS) currentSps = MIN_STEP_SPS;


        } else {

          currentSps += currentAccel() * dt;

          if (currentSps > maxSpsMove()) currentSps = maxSpsMove();

          if (currentSps < START_SPS) currentSps = START_SPS;

        }


        // keep dir aligned (no oscillation)

        applyDir((rem > 0) ? +1 : -1);

      }

    }

  }


  // ---------- STEP GENERATION (bounded catch-up + backlog drop) ----------

  if (currentSps >= MIN_STEP_SPS) {

    uint32_t intervalUs = (uint32_t)(1000000.0f / currentSps);

    if (intervalUs < STEP_PULSE_US + 2) intervalUs = STEP_PULSE_US + 2;


    const uint8_t MAX_STEPS_PER_LOOP = 4;

    uint8_t stepsDone = 0;


    uint32_t nowLocal = micros();

    while ((int32_t)(nowLocal - nextStepAtUs) >= 0 && stepsDone < MAX_STEPS_PER_LOOP) {

      // Stop exactly on target

      if (mode == MODE_MOVE && !reversing) {

        int64_t rem = targetSteps - posSteps;

        if (rem == 0) { mode = MODE_IDLE; currentSps = 0.0f; break; }

        applyDir((rem > 0) ? +1 : -1);

      }


      stepPulse();

      nextStepAtUs += intervalUs;

      stepsDone++;

      nowLocal = micros();


      if (mode == MODE_MOVE && posSteps == targetSteps) {

        mode = MODE_IDLE;

        currentSps = 0.0f;

        reversing = false;

        break;

      }

    }


    // drop backlog instead of bursting

    if ((int32_t)(nowLocal - nextStepAtUs) >= 0 && stepsDone >= MAX_STEPS_PER_LOOP) {

      nextStepAtUs = nowLocal + intervalUs;

    }

  }

}
