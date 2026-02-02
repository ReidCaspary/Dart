"""
Centralized Configuration Module

Contains all configurable constants and default values for the Dart Delivery System.
"""

from dataclasses import dataclass
from typing import List, Tuple


# =============================================================================
# SERIAL COMMUNICATION
# =============================================================================

# Available baud rates for serial connections
SERIAL_BAUD_RATES: List[int] = [9600, 19200, 38400, 57600, 115200, 230400]

# Default baud rate for winch controller (Arduino)
SERIAL_BAUD_DEFAULT: int = 115200

# Serial timeout in seconds
SERIAL_TIMEOUT: float = 0.1

# Serial write timeout in seconds
SERIAL_WRITE_TIMEOUT: float = 0.1


# =============================================================================
# STATUS POLLING
# =============================================================================

# Winch controller status poll interval in seconds
WINCH_POLL_INTERVAL_SEC: float = 0.15  # 150ms

# Drop cylinder status poll interval in seconds
DROP_CYLINDER_POLL_INTERVAL_SEC: float = 0.2  # 200ms


# =============================================================================
# WINCH MOTOR CONFIGURATION
# =============================================================================

# Steps per revolution for the stepper motor (depends on drive microstepping)
STEPS_PER_REVOLUTION: int = 4000

# Default maximum jog speed in revolutions per second
DEFAULT_JOG_SPEED_RPS: float = 10.0

# Default maximum move speed in revolutions per second
DEFAULT_MOVE_SPEED_RPS: float = 7.5

# Acceleration in revolutions per second squared
ACCELERATION_RPS2: float = 1.5

# Deceleration (hard stop) in revolutions per second squared
DECELERATION_RPS2: float = 8.5


# =============================================================================
# DROP CYLINDER CONFIGURATION
# =============================================================================

# Default TCP port for drop cylinder WiFi connection
DROP_CYLINDER_TCP_PORT: int = 8080

# Drop cylinder WiFi Access Point credentials (for initial setup)
DROP_CYLINDER_AP_SSID: str = "DropCylinder"
DROP_CYLINDER_AP_PASSWORD: str = "dropcyl123"

# Servo PWM configuration (microseconds)
SERVO_PWM_MIN_US: int = 1000      # Full speed CCW (up)
SERVO_PWM_NEUTRAL_US: int = 1500  # Stop/neutral
SERVO_PWM_MAX_US: int = 2000      # Full speed CW (down)
SERVO_PWM_FREQUENCY_HZ: int = 50  # 50Hz = 20ms period

# Default servo speed percentage
DEFAULT_SERVO_SPEED_PERCENT: int = 50

# Trim adjustment range (microseconds)
TRIM_MIN_US: int = -50
TRIM_MAX_US: int = 50


# =============================================================================
# CAMERA CONFIGURATION
# =============================================================================

# Camera MJPEG stream port
CAMERA_STREAM_PORT: int = 81

# Camera control port
CAMERA_CONTROL_PORT: int = 80

# Camera connection timeout in seconds
CAMERA_CONNECT_TIMEOUT: float = 10.0

# Camera read timeout in seconds
CAMERA_READ_TIMEOUT: float = 5.0

# Camera discovery scan timeout per IP in seconds
CAMERA_SCAN_TIMEOUT: float = 0.3

# Default display sizes for camera panel
CAMERA_DISPLAY_SIZES: dict = {
    '240x180': (240, 180),
    '320x240': (320, 240),
    '640x480': (640, 480),
    '800x600': (800, 600),
}

# Default camera display size
CAMERA_DEFAULT_SIZE: str = '240x180'


# =============================================================================
# GUI CONFIGURATION
# =============================================================================

# Main window settings
WINDOW_MIN_WIDTH: int = 900
WINDOW_MIN_HEIGHT: int = 750
WINDOW_TITLE: str = "Dart Delivery System"

# Button debounce for long-press detection (milliseconds)
BUTTON_LONG_PRESS_MS: int = 1200

# Button debounce time (milliseconds)
BUTTON_DEBOUNCE_MS: int = 25


# =============================================================================
# ARDUINO PIN DEFINITIONS (for reference)
# =============================================================================

@dataclass(frozen=True)
class WinchControllerPins:
    """Pin definitions for the Arduino Uno R4 winch controller."""
    STEP: int = 8
    DIR: int = 9
    ENABLE: int = 10
    HOME_BUTTON: int = 5
    WELL_BUTTON: int = 4
    JOG_LEFT_BUTTON: int = 2
    JOG_RIGHT_BUTTON: int = 3
    ESTOP: int = 6


@dataclass(frozen=True)
class DropCylinderPins:
    """Pin definitions for the ESP32 Nano drop cylinder controller."""
    SERVO_PWM: str = "D2"  # GPIO D2


# Pin configuration instances
WINCH_PINS = WinchControllerPins()
DROP_CYLINDER_PINS = DropCylinderPins()
