"""
Command Protocol Module

Defines serial command format and response parsing for the winch controller.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import (
    STEPS_PER_REVOLUTION,
    DEFAULT_JOG_SPEED_RPS,
    DEFAULT_MOVE_SPEED_RPS,
)


class MotionMode(Enum):
    """Motor motion modes."""
    IDLE = "IDLE"
    JOG = "JOG"
    MOVE = "MOVE"
    UNKNOWN = "UNKNOWN"


@dataclass
class WinchStatus:
    """Parsed status response from the Arduino."""
    position: int = 0
    mode: MotionMode = MotionMode.IDLE
    speed_rps: float = 0.0
    home_saved: bool = False
    home_position: Optional[int] = None
    well_saved: bool = False
    well_position: Optional[int] = None
    estop_active: bool = False
    max_jog_rps: float = DEFAULT_JOG_SPEED_RPS
    max_move_rps: float = DEFAULT_MOVE_SPEED_RPS
    raw_response: str = ""

    @property
    def position_revolutions(self) -> float:
        """Convert position to revolutions."""
        return self.position / STEPS_PER_REVOLUTION


class Commands:
    """Serial command definitions."""

    # Jog commands
    JOG_LEFT = "JL"
    JOG_RIGHT = "JR"
    JOG_STOP = "JS"

    # Motion commands
    GO_HOME = "GH"
    GO_WELL = "GW"
    STOP = "ST"

    # Save commands
    SAVE_HOME = "SH"
    SAVE_WELL = "SW"

    # Position commands
    ZERO_POSITION = "ZP"

    # Query command
    STATUS = "?"

    @staticmethod
    def go_to_position(steps: int) -> str:
        """Generate absolute position command."""
        return f"GT{steps}"

    @staticmethod
    def move_relative(steps: int) -> str:
        """Generate relative move command."""
        return f"MR{steps}"

    @staticmethod
    def set_jog_speed(rps: float) -> str:
        """Set jog speed in RPS."""
        return f"VJ{rps:.2f}"

    @staticmethod
    def set_move_speed(rps: float) -> str:
        """Set move speed in RPS."""
        return f"VM{rps:.2f}"


class ResponseParser:
    """Parses status responses from the Arduino."""

    # Regex pattern for parsing status response
    # Format: POS:<steps> MODE:<IDLE|JOG|MOVE> SPD:<rps> HOME:<Y@steps|N> WELL:<Y@steps|N> ESTOP:<0|1> VJOG:<rps> VMOVE:<rps>
    STATUS_PATTERN = re.compile(
        r"POS:(-?\d+)\s+"
        r"MODE:(\w+)\s+"
        r"SPD:([\d.]+)\s+"
        r"HOME:(Y@(-?\d+)|N)\s+"
        r"WELL:(Y@(-?\d+)|N)\s+"
        r"ESTOP:([01])"
        r"(?:\s+VJOG:([\d.]+))?"
        r"(?:\s+VMOVE:([\d.]+))?"
    )

    @classmethod
    def parse_status(cls, response: str) -> Optional[WinchStatus]:
        """
        Parse a status response string into a WinchStatus object.

        Args:
            response: Raw response string from Arduino

        Returns:
            WinchStatus object if parsing successful, None otherwise
        """
        if not response:
            return None

        # Clean up the response
        response = response.strip()

        match = cls.STATUS_PATTERN.search(response)
        if not match:
            return None

        # Extract matched groups
        pos_str, mode_str, speed_str = match.group(1), match.group(2), match.group(3)
        home_full, home_pos = match.group(4), match.group(5)
        well_full, well_pos = match.group(6), match.group(7)
        estop_str = match.group(8)
        vjog_str = match.group(9)
        vmove_str = match.group(10)

        # Parse mode
        try:
            mode = MotionMode(mode_str)
        except ValueError:
            mode = MotionMode.UNKNOWN

        # Parse home position
        home_saved = home_full.startswith("Y")
        home_position = int(home_pos) if home_pos else None

        # Parse well position
        well_saved = well_full.startswith("Y")
        well_position = int(well_pos) if well_pos else None

        # Parse speed settings (with defaults if not present)
        max_jog_rps = float(vjog_str) if vjog_str else DEFAULT_JOG_SPEED_RPS
        max_move_rps = float(vmove_str) if vmove_str else DEFAULT_MOVE_SPEED_RPS

        return WinchStatus(
            position=int(pos_str),
            mode=mode,
            speed_rps=float(speed_str),
            home_saved=home_saved,
            home_position=home_position,
            well_saved=well_saved,
            well_position=well_position,
            estop_active=(estop_str == "1"),
            max_jog_rps=max_jog_rps,
            max_move_rps=max_move_rps,
            raw_response=response
        )


def format_command(command: str) -> bytes:
    """
    Format a command for serial transmission.

    Args:
        command: Command string

    Returns:
        Bytes with newline terminator
    """
    return (command.strip() + "\n").encode('ascii')


def validate_steps(value: str) -> Optional[int]:
    """
    Validate and parse a steps input value.

    Args:
        value: String value to parse

    Returns:
        Integer steps if valid, None otherwise
    """
    try:
        # Remove any whitespace and convert
        cleaned = value.strip().replace(",", "")
        return int(cleaned)
    except (ValueError, AttributeError):
        return None
