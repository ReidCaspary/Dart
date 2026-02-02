"""
Drop Cylinder Protocol Module

Defines command format and response parsing for the ESP32 drop cylinder controller.
Mirrors the structure of command_protocol.py for the main winch.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import (
    DEFAULT_SERVO_SPEED_PERCENT,
    TRIM_MIN_US,
    TRIM_MAX_US,
)


class DropCylinderMode(Enum):
    """Drop cylinder motion modes."""
    IDLE = "IDLE"
    JOG_DOWN = "JOG_DOWN"
    JOG_UP = "JOG_UP"
    MOVE_TO_START = "MOVE_START"
    MOVE_TO_STOP = "MOVE_STOP"
    UNKNOWN = "UNKNOWN"


class DropCylinderWifiMode(Enum):
    """WiFi connection modes for the ESP32."""
    ACCESS_POINT = "AP"
    STATION = "STA"
    UNKNOWN = "UNKNOWN"


@dataclass
class DropCylinderStatus:
    """Parsed status response from the ESP32 drop cylinder controller."""
    position_ms: int = 0
    mode: str = "IDLE"
    start_saved: bool = False
    start_position_ms: Optional[int] = None
    stop_saved: bool = False
    stop_position_ms: Optional[int] = None
    trim_us: int = 0
    wifi_mode: str = "AP"
    ip_address: str = ""
    speed_percent: int = DEFAULT_SERVO_SPEED_PERCENT
    raw_response: str = ""

    @property
    def motion_mode(self) -> DropCylinderMode:
        """Get the motion mode as an enum."""
        try:
            return DropCylinderMode(self.mode)
        except ValueError:
            return DropCylinderMode.UNKNOWN

    @property
    def wifi_connection_mode(self) -> DropCylinderWifiMode:
        """Get the WiFi mode as an enum."""
        try:
            return DropCylinderWifiMode(self.wifi_mode)
        except ValueError:
            return DropCylinderWifiMode.UNKNOWN

    @property
    def is_moving(self) -> bool:
        """Check if the cylinder is currently in motion."""
        return self.mode not in ("IDLE", "UNKNOWN")


class DropCylinderCommands:
    """Command definitions for the drop cylinder controller."""

    # Jog commands
    JOG_DOWN = "JD"
    JOG_UP = "JU"
    JOG_STOP = "JS"

    # Motion commands
    GO_START = "GS"
    GO_STOP = "GP"
    STOP = "ST"

    # Save commands
    SAVE_START = "SS"
    SAVE_STOP = "SP"

    # Position commands
    ZERO = "ZERO"

    # Query command
    STATUS = "?"

    @staticmethod
    def set_trim(offset_us: int) -> str:
        """
        Generate trim adjustment command.

        Args:
            offset_us: Trim offset in microseconds (typically -50 to +50)

        Returns:
            Command string
        """
        # Clamp to valid range
        offset_us = max(TRIM_MIN_US, min(TRIM_MAX_US, offset_us))
        return f"TR{offset_us}"

    @staticmethod
    def set_speed(percent: int) -> str:
        """
        Generate speed setting command.

        Args:
            percent: Speed percentage (0-100)

        Returns:
            Command string
        """
        # Clamp to valid range
        percent = max(0, min(100, percent))
        return f"VS{percent}"

    @staticmethod
    def set_wifi_credentials(ssid: str, password: str) -> str:
        """
        Generate WiFi configuration command.

        Args:
            ssid: Network SSID
            password: Network password

        Returns:
            Command string
        """
        return f"WIFI:{ssid}:{password}"

    @staticmethod
    def clear_wifi() -> str:
        """Generate command to clear stored WiFi credentials."""
        return "WIFI_CLEAR"


class DropCylinderResponseParser:
    """Parses status responses from the ESP32 drop cylinder controller."""

    # Status response format:
    # POS:<ms> MODE:<mode> START:<Y@ms|N> STOP:<Y@ms|N> TRIM:<us> WIFI:<AP|STA> IP:<addr> SPEED:<percent>
    STATUS_PATTERN = re.compile(
        r"POS:(-?\d+)\s+"
        r"MODE:(\w+)\s+"
        r"START:(Y@(-?\d+)|N)\s+"
        r"STOP:(Y@(-?\d+)|N)\s+"
        r"TRIM:(-?\d+)\s+"
        r"WIFI:(\w+)\s+"
        r"IP:([^\s]+)"
        r"(?:\s+SPEED:(\d+))?"
    )

    @classmethod
    def parse_status(cls, response: str) -> Optional[DropCylinderStatus]:
        """
        Parse a status response string into a DropCylinderStatus object.

        Args:
            response: Raw response string from ESP32

        Returns:
            DropCylinderStatus object if parsing successful, None otherwise
        """
        if not response or not response.startswith("POS:"):
            return None

        response = response.strip()
        match = cls.STATUS_PATTERN.search(response)
        if not match:
            return None

        # Extract matched groups
        pos_str = match.group(1)
        mode_str = match.group(2)
        start_full = match.group(3)
        start_pos = match.group(4)
        stop_full = match.group(5)
        stop_pos = match.group(6)
        trim_str = match.group(7)
        wifi_str = match.group(8)
        ip_str = match.group(9)
        speed_str = match.group(10)

        # Parse start position
        start_saved = start_full.startswith("Y") if start_full else False
        start_position_ms = int(start_pos) if start_pos else None

        # Parse stop position
        stop_saved = stop_full.startswith("Y") if stop_full else False
        stop_position_ms = int(stop_pos) if stop_pos else None

        # Parse speed (with default)
        speed_percent = int(speed_str) if speed_str else DEFAULT_SERVO_SPEED_PERCENT

        return DropCylinderStatus(
            position_ms=int(pos_str),
            mode=mode_str,
            start_saved=start_saved,
            start_position_ms=start_position_ms,
            stop_saved=stop_saved,
            stop_position_ms=stop_position_ms,
            trim_us=int(trim_str),
            wifi_mode=wifi_str,
            ip_address=ip_str,
            speed_percent=speed_percent,
            raw_response=response
        )


def format_drop_cylinder_command(command: str) -> bytes:
    """
    Format a command for transmission to the drop cylinder controller.

    Args:
        command: Command string

    Returns:
        Bytes with newline terminator
    """
    return (command.strip() + "\n").encode('ascii')


def validate_trim(value: str) -> Optional[int]:
    """
    Validate and parse a trim input value.

    Args:
        value: String value to parse

    Returns:
        Integer trim offset if valid, None otherwise
    """
    try:
        cleaned = value.strip()
        trim = int(cleaned)
        if TRIM_MIN_US <= trim <= TRIM_MAX_US:
            return trim
        return None
    except (ValueError, AttributeError):
        return None


def validate_speed(value: str) -> Optional[int]:
    """
    Validate and parse a speed percentage value.

    Args:
        value: String value to parse

    Returns:
        Integer speed percentage if valid (0-100), None otherwise
    """
    try:
        cleaned = value.strip()
        speed = int(cleaned)
        if 0 <= speed <= 100:
            return speed
        return None
    except (ValueError, AttributeError):
        return None
