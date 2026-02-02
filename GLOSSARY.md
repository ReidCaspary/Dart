# Dart Delivery System - Glossary

Technical terminology and component reference for the dart delivery system used in oil and gas well completions.

---

## System Overview

The Dart Delivery System is designed to safely deploy darts into a wellhead during hydraulic fracturing operations without requiring personnel to enter the hazardous "red zone" around the wellhead. The system has two main components:

1. **Dart Cylinder** - The transportation device that holds and releases the dart
2. **Pulley System** - The conveyance mechanism that moves the dart cylinder horizontally between the home station and the wellhead

```
HOME STATION                                              WELLHEAD
(Loading Area)                                           (Funnel)

    [Driven Pulley]                                    [Idler Pulley]
         ◯═══════════════════════════════════════════════════◯
          ╲                                                 ╱
           ╲═══════════════════════════════════════════════╱
                              │
                         [Dart Cylinder]
                              │
                         (Winch Line)
```

---

## Physical Components

### Dart Cylinder (a.k.a. Dart Holder Assembly, Dart Launching Tube)

The **dart cylinder** is the cylindrical container that holds and transports a single dart to the wellhead. It is the primary payload of the conveyance system.

- **Function**: Holds a dart and releases it on command into the receiving funnel
- **Loading**: Bottom-loading port where operator inserts dart manually at home station
- **Release Mechanism**: Bottom gate/release valve actuated by radio signal (separate from this software)
- **Alignment Legs**: Angled legs at the base that center the cylinder over the funnel opening
- **Onboard Winch**: Servo-controlled winch for vertical positioning (raising/lowering into funnel)
- **Controller**: Arduino Nano ESP32
- **Code Module**: `wifi_manager.py`, `drop_cylinder_panel.py`

```
        ════════╤════════  ← Suspension Cable
                │
           [WINCH MOTOR]   ← Onboard winch (raises/lowers cylinder)
                │
         ┌──────┴──────┐
         │ DART        │
         │ CYLINDER    │
         │  ┌──────┐   │
         │  │ DART │   │   ← Single dart loaded inside
         │  └──────┘   │
         │             │
         │  [CAMERA]   │   ← Internal camera for release confirmation
         │             │
         ╲  [RELEASE]  ╱   ← Bottom gate (radio-controlled, separate system)
          ╲    ╱╲    ╱
           ╲__╱  ╲__╱      ← Alignment legs
```

**Operational Sequence:**
1. Dart is loaded at home station (outside red zone)
2. Pulley system conveys dart cylinder to position above wellhead
3. Onboard winch lowers dart cylinder into the receiving funnel
4. Dart is released via radio command (separate from this software)
5. Onboard winch raises dart cylinder out of funnel
6. Pulley system returns dart cylinder to home station for reloading

---

### Pulley System (Suspension Cable Conveyance System)

The **pulley system** provides horizontal conveyance, moving the dart cylinder assembly between the home station (loading area) and the wellhead position.

- **Function**: Horizontal transport of dart cylinder
- **Mechanism**: Continuous loop of high-strength cable between two pulleys
- **Driven Pulley**: Located at the home station, powered by NEMA stepper motor via STAC5 drive
- **Idler Pulley**: Located at/near the wellhead funnel assembly
- **Cable**: High-strength line (steel cable, Kevlar rope, or rated synthetic fiber)
- **Controller**: Arduino Uno R4
- **Code Module**: `serial_manager.py`, `control_panel.py`
- **Firmware**: `arduino/winch_controller/winch_controller.ino`

```
HOME STATION                                              WELLHEAD
(Outside Red Zone)                                        (Red Zone)

    ┌─────────────┐                                   ┌─────────────┐
    │   DRIVEN    │                                   │    IDLER    │
    │   PULLEY    │                                   │   PULLEY    │
    │  [STAC5]    │                                   │             │
    │  [NEMA]     │                                   │             │
    └──────◯──────┘                                   └──────◯──────┘
           ║══════════════════════════════════════════════════║
           ║                    SUSPENSION CABLE              ║
           ╚══════════════════════╤═══════════════════════════╝
                                  │
                             [Dart Cylinder]
                                  │
                                  ▼
                              [FUNNEL]
                                  │
                             [WELLHEAD]
```

**Direction Reference:**
- **HOME / LEFT**: Toward the driven pulley (loading station)
- **WELL / RIGHT**: Toward the wellhead and idler pulley

---

### Onboard Winch (Dart Cylinder Winch, Upfit Winch)

The **onboard winch** is mounted directly on top of the dart cylinder and provides vertical positioning control.

- **Function**: Raises and lowers the dart cylinder into/out of the receiving funnel
- **Mechanism**: High-strength, low-diameter line attached to the suspension cable
- **Motor**: Reef's 800is continuous rotation servo
- **Control**: PWM signal (50Hz)
- **Attachment**: Winch line is spliced into the suspension cable loop

```
    ═══════════╤═══════════  ← Suspension Cable
               │
          ┌────┴────┐
          │  WINCH  │  ← Onboard winch motor
          │  MOTOR  │
          └────┬────┘
               │ Winch Line (high-strength, low-diameter)
               │
          ┌────▼────┐
          │  DART   │
          │CYLINDER │
          └─────────┘
               │
               ▼
           [FUNNEL]
```

**Positions:**
- **Up Position**: Dart cylinder raised for horizontal travel
- **Down Position**: Dart cylinder lowered into funnel for dart deployment

---

### Funnel Assembly (Receiving Funnel)

The **funnel assembly** is a flange-mounted component attached to the top of the wellhead that receives darts from the dart cylinder.

- **Function**: Guides darts from the dart cylinder into the wellhead bore
- **Mounting**: Welded or bolted to standard wellhead flange
- **Design**: Interior surface angled to guide dart without sticking or inversion
- **Alignment**: Works with dart cylinder's alignment legs to ensure proper centering

```
         ╲  DART   ╱
          ╲ CYLINDER
           ╲     ╱
            ╲   ╱   ← Alignment legs contact funnel wall
         ┌───╲╱───┐
         │ FUNNEL │
         │   ╲╱   │  ← Angled interior guides dart
         └───┬┬───┘
             ││
         ════╪╪════  ← Wellhead flange
             ││
         [WELLHEAD]
```

---

### Camera System

**ESP32-CAM** modules provide visual monitoring during operations.

- **Function**: Visual confirmation of dart release and alignment
- **Internal Camera**: Located inside dart cylinder to confirm dart release
- **External Cameras**: Optional downward-facing cameras on dart cylinder for alignment verification
- **Stream Format**: MJPEG over HTTP (port 81)
- **Features**: Flash/LED control, snapshot capture
- **Code Module**: `camera_panel.py`
- **Firmware**: `arduino/Camera/Camera.ino`

---

### Stepper Drive (STAC5 IP-120E)

The **stepper drive** powers the driven pulley for horizontal conveyance.

- **Model**: Applied Motion STAC5 IP-120E
- **Function**: Converts step/direction signals into motor phases for the driven pulley
- **Input**: Step pulse, Direction, Enable signals from Arduino
- **Configuration**: 4000 microsteps per revolution

---

## Operational Terminology

### Home Station (Loading Area, Start Position)

The **home station** is the staging area where the dart cylinder is loaded with darts. It is located outside the red zone for operator safety.

- **Location**: Near the driven pulley
- **Activities**: Dart loading, system preparation, operator station
- **Safety**: Personnel remain here during deployment operations

### Red Zone (Hot Zone)

The **red zone** is the high-hazard area around the wellhead (typically 50-100 foot radius) characterized by:

- Extreme pressures (up to 15,000 psi)
- Potential for volatile chemicals
- Risk of toxic gases (e.g., hydrogen sulfide/H2S)
- Heavy machinery hazards

**The primary purpose of this system is to deploy darts without any personnel entering the red zone.**

### Dart Release

The **dart release** is the moment when the dart is dropped from the dart cylinder into the funnel.

- **Trigger**: Radio signal command (separate from this control software)
- **Confirmation**: Internal camera provides visual verification
- **Sequence**: Occurs after dart cylinder is lowered and aligned in the funnel

---

## Motion Terminology

### Jog

**Jogging** is continuous motion that occurs while a button is held. The system moves at a constant speed until the button is released.

- **Pulley Jog**: Left/right movement of the suspension cable (moves dart cylinder toward home or wellhead)
- **Winch Jog**: Up/down movement of the dart cylinder vertical position
- **Speed**: Configurable jog speed (default 10 RPS for pulley)

### Move

A **move** is a controlled motion to a specific target position with acceleration and deceleration profiles.

- **Go Home**: Move dart cylinder to saved home (loading) position
- **Go Well**: Move dart cylinder to saved wellhead position
- **Go To**: Move to absolute step position
- **Move Rel**: Move relative number of steps

### Steps

**Steps** are the fundamental unit of position measurement. One step = one microstep pulse to the stepper drive.

- **Pulley**: 4000 steps = 1 revolution of the driven pulley
- **Position Tracking**: 64-bit signed integer (allows billions of steps)

### RPS (Revolutions Per Second)

**RPS** is the speed unit used for the pulley system.

- 1 RPS = 4000 steps/second (at 4000 steps/rev)
- Max Jog: 10.0 RPS
- Max Move: 7.5 RPS

---

## Position Memory

### Home Position

The **home position** is the saved reference point at the loading station.

- Saved with: `SH` command or SAVE HOME button
- Go to with: `GH` command or GO HOME button
- Keyboard: `H` key

### Well Position

The **well position** is the saved target position above the wellhead funnel.

- Saved with: `SW` command or SAVE WELL button
- Go to with: `GW` command or GO WELL button
- Keyboard: `W` key

---

## Communication

### Serial Communication

USB serial connection between PC and Arduino Uno R4 for pulley system control.

- **Baud Rate**: 115200 (default)
- **Protocol**: ASCII text commands and responses
- **Polling**: Status requested every 150ms

### WiFi Communication

TCP/IP connection to ESP32 for dart cylinder control.

- **AP Mode**: ESP32 creates "DartCylinder" network
- **Station Mode**: ESP32 joins existing WiFi network
- **Port**: 8080 (TCP server)
- **Protocol**: ASCII text commands (same as serial)

### MJPEG Stream

**Motion JPEG** video stream from ESP32-CAM modules.

- **Port**: 81
- **Format**: HTTP with boundary markers
- **Frame Rate**: Variable (depends on resolution)

---

## Safety Components

### E-Stop (Emergency Stop)

Hardware emergency stop circuit that immediately halts all motion.

- **Input**: Pin 6 on Arduino
- **Logic**: Active HIGH (E-stop engaged when HIGH)
- **Behavior**: Controlled deceleration, motor disabled
- **GUI**: Red indicator in status bar when active

### Enable Signal

Control signal that enables/disables the stepper drive.

- **Logic**: Active LOW (motor enabled when LOW)
- **Purpose**: Allows motor to be disabled when not in use
- **Safety**: Motor freewheels when disabled

---

## Motion Modes

### IDLE

No motion occurring. Motor holding position (if enabled).

- **GUI Indicator**: Green LED

### JOG

Continuous motion while jog button held.

- **GUI Indicator**: Orange LED
- **Behavior**: Constant speed, stops when released

### MOVE

Controlled motion to target with acceleration profile.

- **GUI Indicator**: Blue LED
- **Behavior**: Accelerates, cruises, decelerates to target

---

## Trim Adjustment

**Trim** is a fine adjustment to the servo winch neutral point. Due to manufacturing tolerances, servos may not be perfectly stopped at exactly 1500µs.

- **Range**: Typically ±100µs
- **Purpose**: Eliminate servo creep at "stopped" position
- **Adjustment**: Slider in dart cylinder panel
- **Stored**: Saved in ESP32 flash memory

---

## Abbreviations

| Term | Meaning |
|------|---------|
| CW | Clockwise |
| CCW | Counter-clockwise |
| RPS | Revolutions per second |
| PWM | Pulse Width Modulation |
| GPIO | General Purpose Input/Output |
| AP | Access Point (WiFi mode) |
| STA | Station (WiFi client mode) |
| MJPEG | Motion JPEG |
| TCP | Transmission Control Protocol |
| USB | Universal Serial Bus |
| UAV | Unmanned Aerial Vehicle (alternate delivery method) |

---

## Deployment Workflow Summary

1. **Load Dart**: Operator loads dart into dart cylinder at home station (outside red zone)
2. **Convey to Wellhead**: Pulley system moves dart cylinder horizontally to position above funnel
3. **Lower into Funnel**: Onboard winch lowers dart cylinder until alignment legs contact funnel
4. **Release Dart**: Radio command opens release gate, dart drops through funnel into wellhead (separate system)
5. **Raise Cylinder**: Onboard winch raises dart cylinder out of funnel
6. **Return to Home**: Pulley system returns dart cylinder to home station
7. **Repeat**: Process repeats for each dart in the fracking sequence

---

## File Reference

| Term | Code Location |
|------|---------------|
| Configuration | `config.py` - Centralized constants and defaults |
| Pulley Control | `serial_manager.py`, `command_protocol.py` |
| Dart Cylinder | `wifi_manager.py`, `drop_cylinder_protocol.py` |
| Camera System | `camera_manager.py`, `camera_panel.py` |
| Main Window | `gui/main_window.py` |
| GUI Panels | `gui/control_panel.py`, `gui/drop_cylinder_panel.py` |
| Pulley Firmware | `arduino/winch_controller/winch_controller.ino` |
| Dart Cylinder Firmware | `arduino/drop_cylinder/drop_cylinder.ino` |
| Camera Firmware | `arduino/Camera/Camera.ino` |
