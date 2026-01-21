# Winch Control

A Python GUI application for controlling an Arduino-based winch system over serial USB. This desktop application provides a user-friendly interface for operating a NEMA 32 winch motor through a STAC5 IP-120E stepper drive.

## Features

- **Real-time Position Display**: Large, easy-to-read position in steps and revolutions
- **Jog Control**: Press-and-hold jog buttons with keyboard support (arrow keys)
- **Position Memory**: Save and recall home/well positions
- **Absolute & Relative Moves**: Go to specific positions or move by step count
- **E-Stop Monitoring**: Visual warning when E-stop is active
- **Status Polling**: Automatic 150ms status updates from Arduino
- **Thread-Safe Communication**: Non-blocking serial on background thread

## Hardware Requirements

### Components

- Arduino Uno R4 (or compatible Arduino board)
- STAC5 IP-120E Stepper Drive
- NEMA 32 stepper motor (or compatible)
- Physical control buttons (optional)
- E-stop switch (optional but recommended)

### Wiring Diagram

```
Arduino Uno R4          STAC5 IP-120E
─────────────────       ─────────────
Pin 9 (STEP)    ───────► STEP+
GND             ───────► STEP-
Pin 8 (DIR)     ───────► DIR+
GND             ───────► DIR-
Pin 7 (ENABLE)  ───────► ENABLE+
GND             ───────► ENABLE-

Physical Buttons (Optional - Active LOW with internal pullups):
Pin 2  ◄─── Jog Left Button ──── GND
Pin 3  ◄─── Jog Right Button ─── GND
Pin 4  ◄─── Go Home Button ───── GND
Pin 5  ◄─── Go Well Button ───── GND
Pin 6  ◄─── E-Stop Switch ────── GND
```

### Drive Configuration

Configure the STAC5 IP-120E for:
- **Microstepping**: 4000 steps/revolution (or adjust `STEPS_PER_REV` in Arduino sketch)
- **Step Input**: Active HIGH, 2μs minimum pulse width
- **Direction Input**: HIGH = CW, LOW = CCW (or as needed)
- **Enable**: Active LOW (motor enabled when pin is LOW)

## Installation

### Prerequisites

- Python 3.8 or higher
- Arduino IDE (for uploading the sketch)

### Python Setup

1. Clone or download this repository:
   ```bash
   cd winch-control
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Arduino Setup

1. Open `arduino/winch_controller.ino` in Arduino IDE

2. Adjust pin definitions if needed (lines 15-23):
   ```cpp
   const int PIN_STEP = 9;
   const int PIN_DIR = 8;
   const int PIN_ENABLE = 7;
   // etc.
   ```

3. Adjust motor configuration if needed (lines 29-35):
   ```cpp
   const long STEPS_PER_REV = 4000;
   const float MAX_SPEED = 8000.0;
   const float JOG_SPEED = 4000.0;
   const float ACCEL = 4000.0;
   ```

4. Upload to Arduino

## Usage

### Starting the Application

```bash
python run.py
```

### GUI Layout

```
┌─────────────────────────────────────────┐
│  Port: [COM3 ▼] [↻] Baud: [115200 ▼] [Connect] │
├─────────────────────────────────────────┤
│              ┌─────────────┐            │
│   Position   │   12,345    │  steps     │
│              └─────────────┘            │
│                 3.086 rev               │
│                                         │
│   Speed: 0.00 RPS    Mode: [  IDLE  ]   │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐     │
│  │ ◄ JOG LEFT   │  │  JOG RIGHT ► │     │
│  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────┤
│  [GO HOME]  [GO WELL]                   │
│                                         │
│  Go To: [________] [GO]                 │
│  Move Rel: [______] [MOVE]              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │             STOP                │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  Home: 0 steps         [SAVE HOME]      │
│  Well: 8,000 steps     [SAVE WELL]      │
│                                         │
│          [ZERO POSITION]                │
├─────────────────────────────────────────┤
│  Status: ● Connected   Last: 14:32:15   │
│  Sent: ?   Recv: POS:12345 MODE:IDLE... │
└─────────────────────────────────────────┘
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Left Arrow | Jog left (hold) |
| Right Arrow | Jog right (hold) |
| Spacebar | Stop |
| Escape | Stop |
| H | Go to home position |
| W | Go to well position |

### Workflow Example

1. **Connect**: Select COM port, click Connect
2. **Set Home**: Jog to home position, click SAVE HOME
3. **Set Well**: Jog to well/target position, click SAVE WELL
4. **Operate**: Use GO HOME / GO WELL buttons to move between positions
5. **Fine Adjust**: Use jog buttons or relative moves for precise positioning

## Serial Protocol

### Commands (sent to Arduino)

| Command | Description |
|---------|-------------|
| `JL` | Start jog left (continuous) |
| `JR` | Start jog right (continuous) |
| `JS` | Stop jogging |
| `GH` | Go to saved home position |
| `GW` | Go to saved well position |
| `SH` | Save current position as home |
| `SW` | Save current position as well |
| `GT<steps>` | Go to absolute position (e.g., `GT50000`) |
| `MR<steps>` | Move relative (e.g., `MR-1000`) |
| `ST` | Stop all motion (controlled deceleration) |
| `?` | Request status |

### Status Response Format

```
POS:<steps> MODE:<IDLE|JOG|MOVE> SPD:<rps> HOME:<Y@steps|N> WELL:<Y@steps|N> ESTOP:<0|1>
```

Example:
```
POS:12345 MODE:IDLE SPD:0.00 HOME:Y@0 WELL:Y@8000 ESTOP:0
```

## Project Structure

```
winch-control/
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── run.py                  # Application entry point
├── arduino/
│   └── winch_controller.ino   # Arduino sketch
├── src/
│   ├── __init__.py
│   ├── main.py             # Application initialization
│   ├── serial_manager.py   # Serial communication handler
│   ├── command_protocol.py # Command definitions & parsing
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py     # Main application window
│       ├── control_panel.py   # Jog and motion controls
│       ├── position_display.py # Position/speed/mode display
│       ├── settings_panel.py  # Home/well save controls
│       └── status_bar.py      # Connection and E-stop status
└── tests/
    ├── __init__.py
    ├── test_command_protocol.py
    └── test_serial_manager.py
```

## Running Tests

```bash
python -m pytest tests/
```

Or with unittest:

```bash
python -m unittest discover tests
```

## Troubleshooting

### Connection Issues

- **Port not listed**: Click refresh button, check USB connection
- **Connection fails**: Ensure Arduino is not in use by Serial Monitor
- **No response**: Verify baud rate matches (default 115200)

### Motion Issues

- **Motor doesn't move**: Check ENABLE pin logic (may need inversion)
- **Wrong direction**: Swap DIR pin HIGH/LOW in Arduino sketch
- **Speed too slow/fast**: Adjust `MAX_SPEED` and `JOG_SPEED` constants
- **Jerky motion**: Lower `ACCEL` value for smoother acceleration

### E-Stop

- **Always showing active**: Check E-stop wiring (should be HIGH when not pressed)
- **Not detecting**: Verify PIN_ESTOP assignment

## Customization

### Changing Steps Per Revolution

In `arduino/winch_controller.ino`:
```cpp
const long STEPS_PER_REV = 4000;  // Change to match your drive settings
```

### Changing Speed Limits

In `arduino/winch_controller.ino`:
```cpp
const float MAX_SPEED = 8000.0;   // Maximum speed (steps/sec)
const float JOG_SPEED = 4000.0;   // Jog speed (steps/sec)
const float ACCEL = 4000.0;       // Acceleration (steps/sec²)
```

### Changing Status Poll Rate

In `src/serial_manager.py`:
```python
POLL_INTERVAL = 0.15  # Seconds between status polls
```

## License

This project is provided as-is for educational and personal use.

## Safety Notice

- Always test with the motor disconnected first
- Ensure E-stop is properly wired and functional
- Never bypass safety interlocks
- Keep hands clear of moving parts
- Use appropriate motor and drive ratings for your load
