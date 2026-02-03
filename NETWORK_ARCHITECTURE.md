# Dart Delivery System - Network Architecture

This document describes the network architecture and communication patterns for the Dart Delivery System.

---

## Overview

The system uses a **hub-and-spoke model** where the laptop runs the main GUI application (`run.py`) and communicates with multiple smart controllers over the Starlink network. The StAC5 motor controller connects directly via Ethernet, while ESP32 devices connect via WiFi.

```
                         Starlink Router
                    ┌────────────────────────┐
                    │   SSID: Sharewell Wifi │
                    │   Pass: sharewell      │
                    └───────────┬────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        │           │           │           │           │
     Laptop      STAC5       ESP32        Cam1        Cam2
    (run.py)   (Ethernet)  (dart cyl)   (WiFi)      (WiFi)
        │           │           │           │           │
        │       Stepper       Servo      Stream      Stream
        │        Motor        (PWM)      (HTTP)      (HTTP)
        │           │
        │           ▼
        │        Winch
        │        Motor
        │
        └──────► Sends commands to all controllers
```

---

## Communication Pattern

All controllers follow the same pattern:

1. **Laptop sends commands** over network to a controller
2. **Controller receives commands** via TCP server
3. **Controller executes commands** on its hardware
4. **Controller sends status/response** back to laptop

| Controller | Laptop Connects To | Controller Talks To | Protocol |
|------------|-------------------|---------------------|----------|
| STAC5 | `192.168.1.40:7776` | Stepper motor (direct) | TCP (SCL) |
| ESP32 Nano | `192.168.1.10:8080` | Servo winch (PWM) | TCP (custom) |
| Camera 1 | `192.168.1.20:81` | Camera sensor | HTTP (MJPEG) |
| Camera 2 | `192.168.1.21:81` | Camera sensor | HTTP (MJPEG) |

---

## Network Configuration

### Starlink Network

All devices connect to the Starlink router. The STAC5 connects via Ethernet for reliable motor control, while ESP32 devices connect via WiFi.

```
Starlink Router
├── WiFi Network
│   ├── SSID: Sharewell Wifi
│   └── Password: sharewell
│
├── Ethernet Ports
│   └── STAC5 .............. Static: 192.168.1.40
│
└── WiFi Clients
    ├── Laptop ............. DHCP (e.g., 192.168.1.100)
    ├── ESP32 Nano ......... Static: 192.168.1.10
    ├── Camera 1 ........... Static: 192.168.1.20
    └── Camera 2 ........... Static: 192.168.1.21
```

---

## Device Details

### STAC5 IP-120E (Winch Motor Controller)

**Role:** Controls the winch motor for vertical positioning

**Connections:**
- Ethernet → Starlink Router (receives commands from laptop)
- Direct → Stepper motor (NEMA 32)

**Communication:**
- IP Address: 192.168.1.40
- Port: 7776
- Protocol: SCL (Applied Motion Products)

**SCL Commands (from Laptop to STAC5):**
| Command | Description |
|---------|-------------|
| `CJ` | Commence jogging |
| `SJ` | Stop jogging |
| `DI` | Set distance (steps) |
| `VE` | Set velocity (rev/sec) |
| `FL` | Feed to length (execute move) |
| `EP` | Read encoder position |
| `AR` | Alarm reset |

See `Host-Command/Host-Command.md` for complete SCL protocol documentation.

---

### ESP32 Nano (Dart Cylinder Controller)

**Role:** Controls the onboard winch (vertical positioning of dart cylinder)

**Connections:**
- WiFi → Starlink Router (receives commands from laptop)
- GPIO → Reef's 800is servo (PWM control)

**Software:**
- Runs a TCP server (port 8080)
- Accepts commands from laptop
- Controls servo via PWM

**IP Address:** 192.168.1.10

**Commands:**
| Command | Description |
|---------|-------------|
| `JU` / `JD` | Jog up / down |
| `JS` | Stop jogging |
| `GS` / `GP` | Go to start / stop position |
| `SS` / `SP` | Save start / stop position |
| `ST` | Stop all motion |
| `?` | Request status |

---

### ESP32-CAM x2 (Cameras)

**Role:** Provide video streams for visual monitoring

**Connections:**
- WiFi → Starlink Router

**Software:**
- HTTP server on port 80 (web interface)
- MJPEG stream on port 81

**IP Addresses:**
- Camera 1: 192.168.1.20
- Camera 2: 192.168.1.21

---

## Laptop Application (run.py)

The laptop runs the main GUI application that:

1. **Connects to all controllers** over the network
2. **Sends commands** based on user input (buttons, keyboard)
3. **Receives status updates** from each controller
4. **Displays camera streams** in the GUI

### Connection Summary

```python
# Winch Motor (direct to STAC5)
stac5_host = "192.168.1.40"
stac5_port = 7776

# Dart Cylinder (via ESP32 Nano)
cylinder_host = "192.168.1.10"
cylinder_port = 8080

# Cameras (HTTP streams)
camera1_url = "http://192.168.1.20:81/stream"
camera2_url = "http://192.168.1.21:81/stream"
```

---

## Why This Architecture?

### Direct Communication
- Laptop communicates directly with STAC5 over Ethernet
- No intermediate controller (Raspberry Pi removed)
- Lower latency for motor control commands

### Separation of Concerns
- STAC5 handles stepper motor control natively
- ESP32 handles servo winch independently
- Each camera streams independently

### Same Pattern Everywhere
- All devices run TCP servers
- Same command/response protocol style
- Easy to understand and debug

### Reliability
- STAC5 has dedicated Ethernet (not affected by WiFi issues)
- WiFi reconnection logic on all ESP32 devices
- Controllers can operate independently

### Flexibility
- Can swap Starlink for any router
- Can run GUI from any laptop on the network
- Easy to add more controllers/cameras

---

## WiFi Credentials

**Network:** Sharewell Wifi
**Password:** sharewell

All ESP32 devices are configured with these credentials:
- `arduino/drop_cylinder/drop_cylinder.ino`
- `arduino/Camera1/Camera1.ino`
- `arduino/Camera2/Camera2.ino`
- `arduino/Camera/Camera.ino`

---

## File Reference

| Component | Firmware/Software |
|-----------|------------------|
| STAC5 | Hardware controller (configured via network) |
| ESP32 Nano | `arduino/drop_cylinder/drop_cylinder.ino` |
| Camera 1 | `arduino/Camera1/Camera1.ino` |
| Camera 2 | `arduino/Camera2/Camera2.ino` |
| Laptop GUI | `run.py`, `src/` |

---

## Quick Reference: IP Addresses

| Device | IP Address | Port | Protocol | Connection |
|--------|------------|------|----------|------------|
| STAC5 | 192.168.1.40 | 7776 | TCP (SCL) | Ethernet |
| ESP32 Nano | 192.168.1.10 | 8080 | TCP | WiFi |
| Camera 1 | 192.168.1.20 | 80, 81 | HTTP | WiFi |
| Camera 2 | 192.168.1.21 | 80, 81 | HTTP | WiFi |
| Laptop | DHCP | - | Client | WiFi/Ethernet |
