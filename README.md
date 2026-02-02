# Dart Delivery System

Industrial dart/ball delivery system for fracking wellhead operations. This system automates the precise delivery of frac balls and darts to the wellhead using a motorized pulley system and pneumatic drop cylinder.

## System Overview

```
                              ┌─────────────────┐
                              │   DROP CYLINDER │ ← Holds darts/balls
                              │   ┌─────────┐   │    Servo winch dispenses
                              │   │ ░░░░░░░ │   │
                              │   │ Darts   │   │
                              │   └─────────┘   │
                              │   [Camera 1]    │ ← Mounted cameras for
                              │   [Camera 2]    │   visual monitoring
                              └────────┬────────┘
                                       │
         ══════════════════════════════╪══════════════════════════════
                    PULLEY SYSTEM (horizontal travel)
         ══════════════════════════════╪══════════════════════════════
                                       │
                                       │  WINCH (vertical travel)
                                       │
                              ┌────────▼────────┐
                              │    WELLHEAD     │
                              └─────────────────┘
```

### Physical Components

| Component | Description | Controller |
|-----------|-------------|------------|
| **Drop Cylinder** | Pressurized cylinder containing darts/balls to be delivered | ESP32 + Servo Winch |
| **Pulley System** | Horizontal conveyance system for positioning drop cylinder | Arduino + Stepper |
| **Winch** | Raises/lowers the drop cylinder assembly to the wellhead | Arduino + Stepper |
| **Camera System** | Two ESP32-CAMs mounted on drop cylinder for monitoring | ESP32-CAM modules |

### Software Control

The Python GUI application (`run.py`) provides centralized control of:

- **Winch Motor** - Stepper motor control for vertical positioning
- **Pulley Motor** - Horizontal positioning via the pulley system
- **Drop Cylinder Servo** - PWM-controlled servo winch for dart dispensing
- **Camera Feeds** - Live MJPEG video streams from both cameras

## Quick Start

### Prerequisites

- Python 3.8+
- Arduino IDE (for firmware upload)
- Hardware: Arduino Uno R4, ESP32 Nano, ESP32-CAM modules

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Dart

# Install Python dependencies
pip install -r requirements.txt

# Or just run - dependencies auto-install
python run.py
```

### Firmware Upload

Upload firmware to each controller using Arduino IDE:

| Controller | Firmware Location | Board Setting |
|------------|-------------------|---------------|
| Main Winch | `winch-control/arduino/winch_controller/` | Arduino Uno R4 |
| Drop Cylinder | `winch-control/arduino/drop_cylinder/` | Arduino Nano ESP32 |
| Cameras | `winch-control/arduino/Camera/` | AI Thinker ESP32-CAM |

### Running the Application

```bash
python run.py
```

## Hardware Configuration

### Main Winch (Arduino Uno R4)

Controls the NEMA 32 stepper motor through a STAC5 IP-120E stepper drive.

**Connections:**
```
Arduino Pin    STAC5 Drive     Function
───────────    ───────────     ────────
Pin 8          STEP+           Step pulse (4000 steps/rev)
Pin 9          DIR+            Direction control
Pin 10         ENABLE+         Motor enable (active LOW)
GND            STEP-/DIR-/EN-  Common ground

Pin 2          Button → GND    Jog Left
Pin 3          Button → GND    Jog Right
Pin 4          Button → GND    Go Well
Pin 5          Button → GND    Go Home
Pin 6          Switch → GND    E-Stop (active HIGH)
```

### Drop Cylinder (ESP32 Nano)

Controls the Reef's 800is servo winch for dart dispensing.

**Connections:**
```
ESP32 Pin      Component       Function
─────────      ─────────       ────────
GPIO D2        Servo Signal    PWM output (50Hz)
GND            Servo GND       Common ground
5V             Servo Power     Servo power supply
```

**Communication:**
- WiFi AP Mode: SSID `DropCylinder`, Password `dropcyl123`
- TCP Server: Port 8080
- Also supports USB serial connection

### Camera System (ESP32-CAM)

Two cameras mounted on the drop cylinder assembly.

**Streams:**
- Video: `http://<camera-ip>:81/stream` (MJPEG)
- Control: `http://<camera-ip>:80/` (Flash, settings)

## GUI Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Port: [COM3 ▼] [↻]  Baud: [115200 ▼]  [Connect]                        │
├───────────────────────────────────┬─────────────────────────────────────┤
│         POSITION DISPLAY          │         DROP CYLINDER               │
│  ┌─────────────────────────────┐  │  WiFi: [192.168.4.1] Port: [8080]   │
│  │         12,345              │  │  [Connect WiFi]  [Connect Serial]   │
│  └─────────────────────────────┘  │                                     │
│           3.086 rev               │  [▲ JOG UP]    [▼ JOG DOWN]         │
│                                   │  [GO START]   [GO STOP]             │
│  Speed: 0.00 RPS  Mode: [IDLE]    │  Speed: [====●=====] 50%            │
├───────────────────────────────────┤  Trim:  [====●=====] 0              │
│         MOTION CONTROL            │                                     │
│  [◄ JOG LEFT]    [JOG RIGHT ►]    ├─────────────────────────────────────┤
│                                   │         CAMERA FEEDS                │
│  [GO HOME]       [GO WELL]        │  ┌─────────────┐  ┌─────────────┐   │
│                                   │  │  Camera 1   │  │  Camera 2   │   │
│  Go To: [_______] [GO]            │  │             │  │             │   │
│  Move Rel: [_____] [MOVE]         │  │   (MJPEG)   │  │   (MJPEG)   │   │
│                                   │  │             │  │             │   │
│  ┌─────────────────────────────┐  │  └─────────────┘  └─────────────┘   │
│  │           STOP              │  │  [Flash 1]  [Snap]  [Flash 2]       │
│  └─────────────────────────────┘  │                                     │
├───────────────────────────────────┴─────────────────────────────────────┤
│  Home: 0 steps    [SAVE HOME]  │  Well: 8,000 steps    [SAVE WELL]      │
│                        [ZERO POSITION]                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  ● Connected   E-Stop: OK   Last: 14:32:15   Sent: ?   Recv: POS:...    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `←` / `→` | Jog winch left/right (hold) |
| `Space` | Stop all motion |
| `Escape` | Stop all motion |
| `H` | Go to home position |
| `W` | Go to well position |

## Serial Protocol Reference

### Main Winch Commands

| Command | Description | Example |
|---------|-------------|---------|
| `JL` / `JR` | Jog left / right | `JL` |
| `JS` | Stop jogging | `JS` |
| `GH` / `GW` | Go to home / well | `GH` |
| `SH` / `SW` | Save home / well position | `SH` |
| `GT<n>` | Go to absolute position | `GT50000` |
| `MR<n>` | Move relative steps | `MR-1000` |
| `ST` | Stop (controlled decel) | `ST` |
| `VJ<n>` | Set jog speed (RPS) | `VJ10.0` |
| `VM<n>` | Set move speed (RPS) | `VM7.5` |
| `?` | Request status | `?` |

**Status Response:**
```
POS:12345 MODE:IDLE SPD:0.00 HOME:Y@0 WELL:Y@8000 ESTOP:0 VJOG:10.00 VMOVE:7.50
```

### Drop Cylinder Commands

| Command | Description | Example |
|---------|-------------|---------|
| `JU` / `JD` | Jog up / down | `JU` |
| `JS` | Stop jogging | `JS` |
| `GS` / `GP` | Go to start / stop position | `GS` |
| `SS` / `SP` | Save start / stop position | `SS` |
| `ST` | Stop motion | `ST` |
| `TR<n>` | Set trim offset (μs) | `TR50` |
| `VS<n>` | Set speed (0-100%) | `VS75` |
| `ZERO` | Zero current position | `ZERO` |
| `?` | Request status | `?` |

**Status Response:**
```
POS:2500 MODE:IDLE START:Y@0 STOP:Y@5000 TRIM:0 WIFI:STA IP:192.168.1.50 SPEED:50
```

## Project Structure

```
Dart/
├── run.py                          # Application entry point
├── README.md                       # This file
├── GLOSSARY.md                     # Hardware terminology reference
├── requirements.txt                # Python dependencies
│
├── src/                            # Python application
│   ├── __init__.py
│   ├── __main__.py                 # Package entry point (python -m src)
│   ├── main.py                     # App initialization
│   ├── config.py                   # Centralized configuration
│   ├── serial_manager.py           # Winch serial communication
│   ├── wifi_manager.py             # Drop cylinder WiFi/serial comm
│   ├── command_protocol.py         # Winch protocol definitions
│   ├── drop_cylinder_protocol.py   # Drop cylinder protocol
│   ├── camera_manager.py           # Camera stream management
│   │
│   └── gui/                        # Tkinter GUI components
│       ├── __init__.py
│       ├── main_window.py          # Main window integration
│       ├── control_panel.py        # Jog & motion controls
│       ├── position_display.py     # Position/speed display
│       ├── drop_cylinder_panel.py  # Drop cylinder controls
│       ├── camera_panel.py         # Video streaming display
│       ├── settings_panel.py       # Position memory controls
│       ├── settings_dialog.py      # Speed settings dialog
│       ├── status_bar.py           # Connection status
│       ├── theme.py                # Dark theme colors
│       └── widgets.py              # Custom widgets
│
├── arduino/                        # Microcontroller firmware
│   ├── winch_controller/           # Arduino Uno R4 - main winch
│   ├── drop_cylinder/              # ESP32 Nano - servo winch
│   └── Camera/                     # ESP32-CAM - video streaming
│
└── tests/                          # Unit tests
    ├── test_command_protocol.py
    └── test_serial_manager.py
```

### Module Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        config.py                            │
│              (Centralized configuration)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│ command_protocol │ │drop_cylinder │ │   camera_manager     │
│    (Winch)       │ │  _protocol   │ │                      │
└────────┬─────────┘ └──────┬───────┘ └──────────┬───────────┘
         │                  │                    │
         ▼                  ▼                    │
┌──────────────────┐ ┌──────────────┐            │
│ serial_manager   │ │ wifi_manager │            │
│    (Winch)       │ │(Drop Cyl)    │            │
└────────┬─────────┘ └──────┬───────┘            │
         │                  │                    │
         └────────┬─────────┴────────────────────┘
                  │
                  ▼
         ┌───────────────┐
         │   gui/        │
         │ main_window   │
         └───────────────┘
```

## Safety

- **E-Stop**: Hardware emergency stop circuit monitored by software
- Always test with motors disconnected first
- Ensure proper grounding of all components
- Keep clear of moving parts during operation
- Never bypass safety interlocks

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port not listed | Click refresh, check USB connection |
| Connection fails | Close Arduino Serial Monitor |
| Motor doesn't move | Check ENABLE pin logic, verify wiring |
| Wrong direction | Swap DIR pin HIGH/LOW in firmware |
| Drop cylinder no WiFi | Check AP mode: "DropCylinder" / "dropcyl123" |
| Camera not streaming | Verify IP address, check port 81 |

## Running Tests

```bash
cd winch-control
python -m pytest tests/
```

## License

Proprietary - Internal use only.
