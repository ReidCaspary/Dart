"""
Unit tests for command_protocol module.
"""

import unittest
from src.command_protocol import (
    Commands,
    ResponseParser,
    WinchStatus,
    MotionMode,
    format_command,
    validate_steps
)


class TestCommands(unittest.TestCase):
    """Tests for command generation."""

    def test_jog_commands(self):
        """Test jog command constants."""
        self.assertEqual(Commands.JOG_LEFT, "JL")
        self.assertEqual(Commands.JOG_RIGHT, "JR")
        self.assertEqual(Commands.JOG_STOP, "JS")

    def test_motion_commands(self):
        """Test motion command constants."""
        self.assertEqual(Commands.GO_HOME, "GH")
        self.assertEqual(Commands.GO_WELL, "GW")
        self.assertEqual(Commands.STOP, "ST")
        self.assertEqual(Commands.STATUS, "?")

    def test_save_commands(self):
        """Test save command constants."""
        self.assertEqual(Commands.SAVE_HOME, "SH")
        self.assertEqual(Commands.SAVE_WELL, "SW")

    def test_go_to_position(self):
        """Test absolute position command generation."""
        self.assertEqual(Commands.go_to_position(0), "GT0")
        self.assertEqual(Commands.go_to_position(50000), "GT50000")
        self.assertEqual(Commands.go_to_position(-1000), "GT-1000")

    def test_move_relative(self):
        """Test relative move command generation."""
        self.assertEqual(Commands.move_relative(500), "MR500")
        self.assertEqual(Commands.move_relative(-1000), "MR-1000")
        self.assertEqual(Commands.move_relative(0), "MR0")


class TestResponseParser(unittest.TestCase):
    """Tests for response parsing."""

    def test_parse_complete_status(self):
        """Test parsing a complete status response."""
        response = "POS:12345 MODE:IDLE SPD:0.00 HOME:Y@0 WELL:Y@8000 ESTOP:0"
        status = ResponseParser.parse_status(response)

        self.assertIsNotNone(status)
        self.assertEqual(status.position, 12345)
        self.assertEqual(status.mode, MotionMode.IDLE)
        self.assertEqual(status.speed_rps, 0.0)
        self.assertTrue(status.home_saved)
        self.assertEqual(status.home_position, 0)
        self.assertTrue(status.well_saved)
        self.assertEqual(status.well_position, 8000)
        self.assertFalse(status.estop_active)

    def test_parse_jog_mode(self):
        """Test parsing status in JOG mode."""
        response = "POS:-5000 MODE:JOG SPD:1.25 HOME:N WELL:N ESTOP:0"
        status = ResponseParser.parse_status(response)

        self.assertIsNotNone(status)
        self.assertEqual(status.position, -5000)
        self.assertEqual(status.mode, MotionMode.JOG)
        self.assertEqual(status.speed_rps, 1.25)
        self.assertFalse(status.home_saved)
        self.assertIsNone(status.home_position)
        self.assertFalse(status.well_saved)
        self.assertIsNone(status.well_position)

    def test_parse_move_mode(self):
        """Test parsing status in MOVE mode."""
        response = "POS:2000 MODE:MOVE SPD:2.00 HOME:Y@0 WELL:N ESTOP:0"
        status = ResponseParser.parse_status(response)

        self.assertIsNotNone(status)
        self.assertEqual(status.mode, MotionMode.MOVE)
        self.assertEqual(status.speed_rps, 2.0)

    def test_parse_estop_active(self):
        """Test parsing with E-stop active."""
        response = "POS:0 MODE:IDLE SPD:0.00 HOME:N WELL:N ESTOP:1"
        status = ResponseParser.parse_status(response)

        self.assertIsNotNone(status)
        self.assertTrue(status.estop_active)

    def test_parse_negative_positions(self):
        """Test parsing negative positions."""
        response = "POS:-12345 MODE:IDLE SPD:0.00 HOME:Y@-5000 WELL:Y@-10000 ESTOP:0"
        status = ResponseParser.parse_status(response)

        self.assertIsNotNone(status)
        self.assertEqual(status.position, -12345)
        self.assertEqual(status.home_position, -5000)
        self.assertEqual(status.well_position, -10000)

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        status = ResponseParser.parse_status("")
        self.assertIsNone(status)

    def test_parse_none_response(self):
        """Test parsing None response."""
        status = ResponseParser.parse_status(None)
        self.assertIsNone(status)

    def test_parse_invalid_response(self):
        """Test parsing invalid response."""
        status = ResponseParser.parse_status("INVALID DATA")
        self.assertIsNone(status)

    def test_parse_partial_response(self):
        """Test parsing partial response."""
        status = ResponseParser.parse_status("POS:12345 MODE:IDLE")
        self.assertIsNone(status)

    def test_position_revolutions_property(self):
        """Test position_revolutions calculation."""
        status = WinchStatus(position=8000)
        self.assertEqual(status.position_revolutions, 2.0)

        status = WinchStatus(position=4000)
        self.assertEqual(status.position_revolutions, 1.0)

        status = WinchStatus(position=2000)
        self.assertEqual(status.position_revolutions, 0.5)


class TestFormatCommand(unittest.TestCase):
    """Tests for command formatting."""

    def test_format_simple_command(self):
        """Test formatting simple commands."""
        self.assertEqual(format_command("JL"), b"JL\n")
        self.assertEqual(format_command("?"), b"?\n")

    def test_format_command_with_value(self):
        """Test formatting commands with values."""
        self.assertEqual(format_command("GT50000"), b"GT50000\n")
        self.assertEqual(format_command("MR-1000"), b"MR-1000\n")

    def test_format_command_strips_whitespace(self):
        """Test that formatting strips whitespace."""
        self.assertEqual(format_command("  JL  "), b"JL\n")
        self.assertEqual(format_command("GT50000\n"), b"GT50000\n")


class TestValidateSteps(unittest.TestCase):
    """Tests for step value validation."""

    def test_validate_positive_integer(self):
        """Test validating positive integers."""
        self.assertEqual(validate_steps("1000"), 1000)
        self.assertEqual(validate_steps("50000"), 50000)

    def test_validate_negative_integer(self):
        """Test validating negative integers."""
        self.assertEqual(validate_steps("-1000"), -1000)
        self.assertEqual(validate_steps("-50000"), -50000)

    def test_validate_zero(self):
        """Test validating zero."""
        self.assertEqual(validate_steps("0"), 0)

    def test_validate_with_whitespace(self):
        """Test validating with whitespace."""
        self.assertEqual(validate_steps("  1000  "), 1000)
        self.assertEqual(validate_steps("\t500\n"), 500)

    def test_validate_with_commas(self):
        """Test validating with comma separators."""
        self.assertEqual(validate_steps("1,000"), 1000)
        self.assertEqual(validate_steps("50,000"), 50000)
        self.assertEqual(validate_steps("1,000,000"), 1000000)

    def test_validate_invalid_string(self):
        """Test validating invalid strings."""
        self.assertIsNone(validate_steps("abc"))
        self.assertIsNone(validate_steps(""))
        self.assertIsNone(validate_steps("12.5"))

    def test_validate_none(self):
        """Test validating None."""
        self.assertIsNone(validate_steps(None))


class TestWinchStatus(unittest.TestCase):
    """Tests for WinchStatus dataclass."""

    def test_default_values(self):
        """Test default status values."""
        status = WinchStatus()

        self.assertEqual(status.position, 0)
        self.assertEqual(status.mode, MotionMode.IDLE)
        self.assertEqual(status.speed_rps, 0.0)
        self.assertFalse(status.home_saved)
        self.assertIsNone(status.home_position)
        self.assertFalse(status.well_saved)
        self.assertIsNone(status.well_position)
        self.assertFalse(status.estop_active)
        self.assertEqual(status.raw_response, "")


class TestMotionMode(unittest.TestCase):
    """Tests for MotionMode enum."""

    def test_mode_values(self):
        """Test mode enum values."""
        self.assertEqual(MotionMode.IDLE.value, "IDLE")
        self.assertEqual(MotionMode.JOG.value, "JOG")
        self.assertEqual(MotionMode.MOVE.value, "MOVE")
        self.assertEqual(MotionMode.UNKNOWN.value, "UNKNOWN")

    def test_mode_from_string(self):
        """Test creating mode from string."""
        self.assertEqual(MotionMode("IDLE"), MotionMode.IDLE)
        self.assertEqual(MotionMode("JOG"), MotionMode.JOG)
        self.assertEqual(MotionMode("MOVE"), MotionMode.MOVE)


if __name__ == "__main__":
    unittest.main()
