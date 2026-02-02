"""
Serial Manager Module

Handles serial port connection, communication, and status polling.
Runs serial operations on a background thread for non-blocking GUI.
"""

import threading
import queue
import time
from typing import Callable, Optional, List
from dataclasses import dataclass
from enum import Enum

import serial
import serial.tools.list_ports

from .config import (
    SERIAL_BAUD_DEFAULT,
    SERIAL_TIMEOUT,
    SERIAL_WRITE_TIMEOUT,
    WINCH_POLL_INTERVAL_SEC,
)
from .command_protocol import (
    Commands,
    WinchStatus,
    ResponseParser,
    format_command
)


class ConnectionState(Enum):
    """Serial connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class SerialConfig:
    """Serial port configuration."""
    port: str = ""
    baudrate: int = SERIAL_BAUD_DEFAULT
    timeout: float = SERIAL_TIMEOUT
    write_timeout: float = SERIAL_WRITE_TIMEOUT


class SerialManager:
    """
    Manages serial communication with the Arduino winch controller.

    Provides thread-safe command sending and status polling.
    """

    # Polling interval in seconds
    POLL_INTERVAL = WINCH_POLL_INTERVAL_SEC

    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self._config = SerialConfig()
        self._state = ConnectionState.DISCONNECTED

        # Threading
        self._read_thread: Optional[threading.Thread] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Command queue for thread-safe sending
        self._command_queue: queue.Queue = queue.Queue()

        # Callbacks
        self._status_callback: Optional[Callable[[WinchStatus], None]] = None
        self._connection_callback: Optional[Callable[[ConnectionState, str], None]] = None
        self._command_sent_callback: Optional[Callable[[str], None]] = None
        self._response_callback: Optional[Callable[[str], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None

        # Last known status
        self._last_status: Optional[WinchStatus] = None
        self._last_response_time: float = 0

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if serial port is connected."""
        return self._state == ConnectionState.CONNECTED

    @property
    def last_status(self) -> Optional[WinchStatus]:
        """Get the last received status."""
        return self._last_status

    @property
    def last_response_time(self) -> float:
        """Get timestamp of last successful response."""
        return self._last_response_time

    @staticmethod
    def list_ports() -> List[str]:
        """Get list of available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def set_status_callback(self, callback: Callable[[WinchStatus], None]) -> None:
        """Set callback for status updates."""
        self._status_callback = callback

    def set_connection_callback(self, callback: Callable[[ConnectionState, str], None]) -> None:
        """Set callback for connection state changes."""
        self._connection_callback = callback

    def set_command_sent_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for when commands are sent."""
        self._command_sent_callback = callback

    def set_response_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for raw responses received."""
        self._response_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for errors."""
        self._error_callback = callback

    def _set_state(self, state: ConnectionState, message: str = "") -> None:
        """Update connection state and notify callback."""
        self._state = state
        if self._connection_callback:
            self._connection_callback(state, message)

    def connect(self, port: str, baudrate: int = 115200) -> bool:
        """
        Connect to the specified serial port.

        Args:
            port: Serial port name (e.g., 'COM3' or '/dev/ttyUSB0')
            baudrate: Baud rate (default 115200)

        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected:
            self.disconnect()

        self._config.port = port
        self._config.baudrate = baudrate
        self._set_state(ConnectionState.CONNECTING, f"Connecting to {port}...")

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=self._config.timeout,
                write_timeout=self._config.write_timeout
            )

            # Clear any pending data
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

            # Small delay for Arduino reset
            time.sleep(0.5)

            # Start background threads
            self._stop_event.clear()

            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()

            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()

            self._set_state(ConnectionState.CONNECTED, f"Connected to {port}")
            return True

        except serial.SerialException as e:
            self._set_state(ConnectionState.ERROR, str(e))
            if self._error_callback:
                self._error_callback(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the serial port."""
        # Signal threads to stop
        self._stop_event.set()

        # Wait for threads to finish
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=1.0)
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)

        # Close serial port
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception:
                    pass
            self._serial = None

        self._last_status = None
        self._set_state(ConnectionState.DISCONNECTED, "Disconnected")

    def send_command(self, command: str) -> bool:
        """
        Send a command to the Arduino.

        Args:
            command: Command string to send

        Returns:
            True if command was queued successfully
        """
        if not self.is_connected:
            return False

        self._command_queue.put(command)
        return True

    def _send_command_direct(self, command: str) -> bool:
        """
        Send a command directly (called from worker thread).

        Args:
            command: Command string to send

        Returns:
            True if sent successfully
        """
        with self._lock:
            if not self._serial or not self._serial.is_open:
                return False

            try:
                data = format_command(command)
                self._serial.write(data)
                self._serial.flush()

                if self._command_sent_callback:
                    self._command_sent_callback(command)

                return True

            except serial.SerialException as e:
                if self._error_callback:
                    self._error_callback(f"Send failed: {e}")
                self._handle_disconnection()
                return False

    def _read_loop(self) -> None:
        """Background thread for reading serial responses."""
        buffer = ""

        while not self._stop_event.is_set():
            # Process any queued commands first
            try:
                while True:
                    command = self._command_queue.get_nowait()
                    self._send_command_direct(command)
            except queue.Empty:
                pass

            # Read available data
            with self._lock:
                if not self._serial or not self._serial.is_open:
                    break

                try:
                    if self._serial.in_waiting > 0:
                        data = self._serial.read(self._serial.in_waiting)
                        buffer += data.decode('ascii', errors='ignore')
                except serial.SerialException as e:
                    if self._error_callback:
                        self._error_callback(f"Read error: {e}")
                    self._handle_disconnection()
                    break

            # Process complete lines
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line:
                    self._process_response(line)

            # Small sleep to prevent busy-waiting
            time.sleep(0.01)

    def _poll_loop(self) -> None:
        """Background thread for periodic status polling."""
        while not self._stop_event.is_set():
            if self.is_connected:
                self._send_command_direct(Commands.STATUS)

            # Wait for poll interval or stop event
            self._stop_event.wait(self.POLL_INTERVAL)

    def _process_response(self, response: str) -> None:
        """
        Process a received response line.

        Args:
            response: Response string from Arduino
        """
        # Notify raw response callback
        if self._response_callback:
            self._response_callback(response)

        # Try to parse as status
        status = ResponseParser.parse_status(response)
        if status:
            self._last_status = status
            self._last_response_time = time.time()

            if self._status_callback:
                self._status_callback(status)

    def _handle_disconnection(self) -> None:
        """Handle unexpected disconnection."""
        self._set_state(ConnectionState.ERROR, "Connection lost")
        # Schedule cleanup on main thread would be done via callback

    # Convenience methods for common commands

    def jog_left(self) -> bool:
        """Start jogging left."""
        return self.send_command(Commands.JOG_LEFT)

    def jog_right(self) -> bool:
        """Start jogging right."""
        return self.send_command(Commands.JOG_RIGHT)

    def jog_stop(self) -> bool:
        """Stop jogging."""
        return self.send_command(Commands.JOG_STOP)

    def go_home(self) -> bool:
        """Go to saved home position."""
        return self.send_command(Commands.GO_HOME)

    def go_well(self) -> bool:
        """Go to saved well position."""
        return self.send_command(Commands.GO_WELL)

    def stop(self) -> bool:
        """Stop all motion."""
        return self.send_command(Commands.STOP)

    def save_home(self) -> bool:
        """Save current position as home."""
        return self.send_command(Commands.SAVE_HOME)

    def save_well(self) -> bool:
        """Save current position as well."""
        return self.send_command(Commands.SAVE_WELL)

    def go_to_position(self, steps: int) -> bool:
        """Go to absolute position."""
        return self.send_command(Commands.go_to_position(steps))

    def move_relative(self, steps: int) -> bool:
        """Move relative steps."""
        return self.send_command(Commands.move_relative(steps))

    def set_jog_speed(self, rps: float) -> bool:
        """Set jog speed in RPS."""
        return self.send_command(Commands.set_jog_speed(rps))

    def set_move_speed(self, rps: float) -> bool:
        """Set move speed in RPS."""
        return self.send_command(Commands.set_move_speed(rps))

    def request_status(self) -> bool:
        """Request status update."""
        return self.send_command(Commands.STATUS)
