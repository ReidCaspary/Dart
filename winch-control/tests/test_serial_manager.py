"""
Unit tests for serial_manager module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading

from src.serial_manager import (
    SerialManager,
    SerialConfig,
    ConnectionState
)
from src.command_protocol import Commands, WinchStatus, MotionMode


class TestSerialConfig(unittest.TestCase):
    """Tests for SerialConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SerialConfig()

        self.assertEqual(config.port, "")
        self.assertEqual(config.baudrate, 115200)
        self.assertEqual(config.timeout, 0.1)
        self.assertEqual(config.write_timeout, 0.1)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SerialConfig(
            port="COM3",
            baudrate=9600,
            timeout=0.5,
            write_timeout=0.5
        )

        self.assertEqual(config.port, "COM3")
        self.assertEqual(config.baudrate, 9600)
        self.assertEqual(config.timeout, 0.5)
        self.assertEqual(config.write_timeout, 0.5)


class TestConnectionState(unittest.TestCase):
    """Tests for ConnectionState enum."""

    def test_state_values(self):
        """Test connection state values."""
        self.assertEqual(ConnectionState.DISCONNECTED.value, "disconnected")
        self.assertEqual(ConnectionState.CONNECTING.value, "connecting")
        self.assertEqual(ConnectionState.CONNECTED.value, "connected")
        self.assertEqual(ConnectionState.ERROR.value, "error")


class TestSerialManagerInit(unittest.TestCase):
    """Tests for SerialManager initialization."""

    def test_initial_state(self):
        """Test initial state of SerialManager."""
        manager = SerialManager()

        self.assertEqual(manager.state, ConnectionState.DISCONNECTED)
        self.assertFalse(manager.is_connected)
        self.assertIsNone(manager.last_status)
        self.assertEqual(manager.last_response_time, 0)


class TestSerialManagerCallbacks(unittest.TestCase):
    """Tests for SerialManager callback registration."""

    def setUp(self):
        self.manager = SerialManager()

    def test_set_status_callback(self):
        """Test setting status callback."""
        callback = Mock()
        self.manager.set_status_callback(callback)
        self.assertEqual(self.manager._status_callback, callback)

    def test_set_connection_callback(self):
        """Test setting connection callback."""
        callback = Mock()
        self.manager.set_connection_callback(callback)
        self.assertEqual(self.manager._connection_callback, callback)

    def test_set_command_sent_callback(self):
        """Test setting command sent callback."""
        callback = Mock()
        self.manager.set_command_sent_callback(callback)
        self.assertEqual(self.manager._command_sent_callback, callback)

    def test_set_response_callback(self):
        """Test setting response callback."""
        callback = Mock()
        self.manager.set_response_callback(callback)
        self.assertEqual(self.manager._response_callback, callback)

    def test_set_error_callback(self):
        """Test setting error callback."""
        callback = Mock()
        self.manager.set_error_callback(callback)
        self.assertEqual(self.manager._error_callback, callback)


class TestSerialManagerListPorts(unittest.TestCase):
    """Tests for port listing."""

    @patch('src.serial_manager.serial.tools.list_ports.comports')
    def test_list_ports(self, mock_comports):
        """Test listing available ports."""
        # Setup mock
        port1 = Mock()
        port1.device = "COM1"
        port2 = Mock()
        port2.device = "COM3"
        mock_comports.return_value = [port1, port2]

        ports = SerialManager.list_ports()

        self.assertEqual(ports, ["COM1", "COM3"])
        mock_comports.assert_called_once()

    @patch('src.serial_manager.serial.tools.list_ports.comports')
    def test_list_ports_empty(self, mock_comports):
        """Test listing ports when none available."""
        mock_comports.return_value = []

        ports = SerialManager.list_ports()

        self.assertEqual(ports, [])


class TestSerialManagerConnection(unittest.TestCase):
    """Tests for connection handling."""

    def setUp(self):
        self.manager = SerialManager()
        self.connection_callback = Mock()
        self.manager.set_connection_callback(self.connection_callback)

    @patch('src.serial_manager.serial.Serial')
    def test_connect_success(self, mock_serial_class):
        """Test successful connection."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        result = self.manager.connect("COM3", 115200)

        self.assertTrue(result)
        self.assertEqual(self.manager.state, ConnectionState.CONNECTED)
        self.assertTrue(self.manager.is_connected)

        # Cleanup
        self.manager.disconnect()

    @patch('src.serial_manager.serial.Serial')
    def test_connect_failure(self, mock_serial_class):
        """Test connection failure."""
        import serial
        mock_serial_class.side_effect = serial.SerialException("Port not found")

        result = self.manager.connect("COM99", 115200)

        self.assertFalse(result)
        self.assertEqual(self.manager.state, ConnectionState.ERROR)
        self.assertFalse(self.manager.is_connected)

    @patch('src.serial_manager.serial.Serial')
    def test_disconnect(self, mock_serial_class):
        """Test disconnection."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        self.manager.connect("COM3", 115200)
        self.manager.disconnect()

        self.assertEqual(self.manager.state, ConnectionState.DISCONNECTED)
        self.assertFalse(self.manager.is_connected)

    def test_send_command_disconnected(self):
        """Test sending command when disconnected."""
        result = self.manager.send_command("JL")
        self.assertFalse(result)


class TestSerialManagerConvenienceMethods(unittest.TestCase):
    """Tests for convenience command methods."""

    def setUp(self):
        self.manager = SerialManager()
        # Mock the send_command method
        self.manager.send_command = Mock(return_value=True)

    def test_jog_left(self):
        """Test jog left method."""
        self.manager.jog_left()
        self.manager.send_command.assert_called_with(Commands.JOG_LEFT)

    def test_jog_right(self):
        """Test jog right method."""
        self.manager.jog_right()
        self.manager.send_command.assert_called_with(Commands.JOG_RIGHT)

    def test_jog_stop(self):
        """Test jog stop method."""
        self.manager.jog_stop()
        self.manager.send_command.assert_called_with(Commands.JOG_STOP)

    def test_go_home(self):
        """Test go home method."""
        self.manager.go_home()
        self.manager.send_command.assert_called_with(Commands.GO_HOME)

    def test_go_well(self):
        """Test go well method."""
        self.manager.go_well()
        self.manager.send_command.assert_called_with(Commands.GO_WELL)

    def test_stop(self):
        """Test stop method."""
        self.manager.stop()
        self.manager.send_command.assert_called_with(Commands.STOP)

    def test_save_home(self):
        """Test save home method."""
        self.manager.save_home()
        self.manager.send_command.assert_called_with(Commands.SAVE_HOME)

    def test_save_well(self):
        """Test save well method."""
        self.manager.save_well()
        self.manager.send_command.assert_called_with(Commands.SAVE_WELL)

    def test_go_to_position(self):
        """Test go to position method."""
        self.manager.go_to_position(50000)
        self.manager.send_command.assert_called_with("GT50000")

    def test_move_relative(self):
        """Test move relative method."""
        self.manager.move_relative(-1000)
        self.manager.send_command.assert_called_with("MR-1000")

    def test_request_status(self):
        """Test request status method."""
        self.manager.request_status()
        self.manager.send_command.assert_called_with(Commands.STATUS)


class TestSerialManagerResponseProcessing(unittest.TestCase):
    """Tests for response processing."""

    def setUp(self):
        self.manager = SerialManager()
        self.status_callback = Mock()
        self.response_callback = Mock()
        self.manager.set_status_callback(self.status_callback)
        self.manager.set_response_callback(self.response_callback)

    def test_process_valid_response(self):
        """Test processing valid status response."""
        response = "POS:12345 MODE:IDLE SPD:0.00 HOME:Y@0 WELL:Y@8000 ESTOP:0"

        # Call the private method directly for testing
        self.manager._process_response(response)

        # Check that callbacks were called
        self.response_callback.assert_called_once_with(response)
        self.status_callback.assert_called_once()

        # Check that last_status was updated
        self.assertIsNotNone(self.manager.last_status)
        self.assertEqual(self.manager.last_status.position, 12345)

    def test_process_invalid_response(self):
        """Test processing invalid response."""
        response = "INVALID DATA"

        self.manager._process_response(response)

        # Response callback should still be called
        self.response_callback.assert_called_once_with(response)

        # Status callback should not be called for invalid data
        self.status_callback.assert_not_called()

        # last_status should remain None
        self.assertIsNone(self.manager.last_status)


if __name__ == "__main__":
    unittest.main()
