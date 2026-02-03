# Dart Delivery System - Network Architecture

This document describes the network architecture and communication patterns for the Dart Delivery System.

---

## Overview

The system uses a **hub-and-spoke model** where the laptop runs the main GUI application (`run.py`) and communicates with multiple smart controllers over WiFi. Each controller handles its own hardware.

```
                         Starlink / Router
                              (WiFi)
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        │           │           │           │           │
     Laptop        Pi        ESP32        Cam1        Cam2
    (run.py)    (pulley)   (dart cyl)
        │           │           │           │           │
        │      Ethernet      Servo       Stream      Stream
        │           │        (PWM)       (HTTP)      (HTTP)
        │           ▼
        │        STAC5
        │           │
        │       Stepper
        │        Motor
        │
        └──────► Sends commands to all controllers over WiFi
```

---

## Communication Pattern

All controllers follow the same pattern:

1. **Laptop sends commands** over WiFi to a controller
2. **Controller receives commands** via TCP server
3. **Controller executes commands** on its hardware
4. **Controller sends status/response** back to laptop

| Controller | Laptop Connects To | Controller Talks To | Protocol |
|------------|-------------------|---------------------|----------|
| Raspberry Pi | `192.168.x.10:8081` | STAC5 (Ethernet) | TCP (custom) |
| ESP32 Nano | `192.168.4.10:8080` | Servo winch (PWM) | TCP (custom) |
| Camera 1 | `192.168.4.20:81` | Camera sensor | HTTP (MJPEG) |
| Camera 2 | `192.168.4.21:81` | Camera sensor | HTTP (MJPEG) |

---

## Network Configuration

### With Starlink/Router (Recommended)

All devices connect to the same WiFi network. The Pi has an additional Ethernet connection to the STAC5.

```
Starlink/Router: 192.168.1.1 (or similar)
        │
        ├── Laptop ............. DHCP (e.g., 192.168.1.100)
        ├── Raspberry Pi ....... Static: 192.168.1.10
        ├── ESP32 Nano ......... Static: 192.168.1.11
        ├── Camera 1 ........... Static: 192.168.1.20
        └── Camera 2 ........... Static: 192.168.1.21

Pi Ethernet (separate network):
        │
        └── STAC5 .............. Static: 192.168.0.40
            Pi eth0 ............ Static: 192.168.0.1
```

### Pi Network Interfaces

| Interface | Network | IP Address | Purpose |
|-----------|---------|------------|---------|
| wlan0 | Starlink WiFi | 192.168.1.10 | Communication with laptop and ESP32s |
| eth0 | Direct to STAC5 | 192.168.0.1 | Communication with STAC5 motor controller |

---

## Device Details

### Raspberry Pi (Pulley Controller)

**Role:** Controls the pulley system (horizontal conveyance)

**Connections:**
- WiFi → Starlink/Router (receives commands from laptop)
- Ethernet → STAC5 IP-120E (sends SCL commands)

**Software:**
- Runs a TCP server (port 8081) that accepts commands from laptop
- Translates commands to SCL protocol
- Sends SCL commands to STAC5 at 192.168.0.40:7776

**Commands (from laptop to Pi):**
| Command | Description |
|---------|-------------|
| `JL` | Jog left (toward home) |
| `JR` | Jog right (toward well) |
| `JS` | Stop jogging |
| `GH` | Go to home position |
| `GW` | Go to well position |
| `SH` | Save current position as home |
| `SW` | Save current position as well |
| `ST` | Stop all motion |
| `?` | Request status |

**SCL Commands (from Pi to STAC5):**
| Command | Description |
|---------|-------------|
| `CJ` | Commence jogging |
| `SJ` | Stop jogging |
| `DI` | Set distance (steps) |
| `VE` | Set velocity (rev/sec) |
| `FL` | Feed to length (execute move) |
| `EP` | Read encoder position |
| `AR` | Alarm reset |

---

### ESP32 Nano (Dart Cylinder Controller)

**Role:** Controls the onboard winch (vertical positioning of dart cylinder)

**Connections:**
- WiFi → Starlink/Router (receives commands from laptop)
- GPIO → Reef's 800is servo (PWM control)

**Software:**
- Runs a TCP server (port 8080)
- Accepts commands from laptop
- Controls servo via PWM

**IP Address:** 192.168.1.11 (or 192.168.4.10 if using Pi as AP)

---

### ESP32-CAM x2 (Cameras)

**Role:** Provide video streams for visual monitoring

**Connections:**
- WiFi → Starlink/Router

**Software:**
- HTTP server on port 80 (web interface)
- MJPEG stream on port 81

**IP Addresses:**
- Camera 1: 192.168.1.20 (or 192.168.4.20)
- Camera 2: 192.168.1.21 (or 192.168.4.21)

---

## Laptop Application (run.py)

The laptop runs the main GUI application that:

1. **Connects to all controllers** over WiFi
2. **Sends commands** based on user input (buttons, keyboard)
3. **Receives status updates** from each controller
4. **Displays camera streams** in the GUI

### Connection Summary

```python
# Pulley System (via Pi)
pulley_host = "192.168.1.10"
pulley_port = 8081

# Dart Cylinder (via ESP32 Nano)
cylinder_host = "192.168.1.11"
cylinder_port = 8080

# Cameras (HTTP streams)
camera1_url = "http://192.168.1.20:81/stream"
camera2_url = "http://192.168.1.21:81/stream"
```

---

## Why This Architecture?

### Separation of Concerns
- Each controller handles its own hardware
- Laptop only deals with high-level commands
- Hardware failures are isolated

### Same Pattern Everywhere
- Pi and ESP32s both run TCP servers
- Same command/response protocol
- Easy to understand and debug

### Reliability
- Controllers can operate independently
- WiFi reconnection logic on all devices
- STAC5 has dedicated Ethernet (not affected by WiFi issues)

### Flexibility
- Can swap Starlink for any router
- Can run GUI from any laptop on the network
- Easy to add more controllers/cameras

---

## File Reference

| Component | Firmware/Software |
|-----------|------------------|
| Raspberry Pi | `src/pi_controller.py` (to be created) |
| ESP32 Nano | `arduino/drop_cylinder/drop_cylinder.ino` |
| Camera 1 | `arduino/Camera1/Camera1.ino` |
| Camera 2 | `arduino/Camera2/Camera2.ino` |
| Laptop GUI | `run.py`, `src/` |

---

## Quick Reference: IP Addresses

| Device | IP Address | Port | Protocol |
|--------|------------|------|----------|
| Raspberry Pi (WiFi) | 192.168.1.10 | 8081 | TCP |
| Raspberry Pi (Ethernet) | 192.168.0.1 | - | - |
| STAC5 | 192.168.0.40 | 7776 | TCP (SCL) |
| ESP32 Nano | 192.168.1.11 | 8080 | TCP |
| Camera 1 | 192.168.1.20 | 80, 81 | HTTP |
| Camera 2 | 192.168.1.21 | 80, 81 | HTTP |
| Laptop | DHCP | - | Client |

*Note: If using Pi as access point instead of Starlink, the 192.168.1.x addresses become 192.168.4.x*
