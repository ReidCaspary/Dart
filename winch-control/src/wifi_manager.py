"""
Drop Cylinder Manager Module

Handles communication with the ESP32 drop cylinder controller.
Supports both WiFi/TCP and USB serial connections.
"""

import socket
import threading
import queue
import time
from typing import Callable, Optional, List
from dataclasses import dataclass
from enum import Enum

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class ConnectionMode(Enum):
    """Connection mode for the drop cylinder controller."""
    WIFI = "wifi"
    SERIAL = "serial"


class DropCylinderConnectionState(Enum):
    """Connection states for drop cylinder controller."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


# Backward compatibility alias
WifiConnectionState = DropCylinderConnectionState


@dataclass
class DropCylinderStatus:
    """Parsed status from the drop cylinder controller."""
    position_ms: int = 0
    mode: str = "IDLE"
    start_saved: bool = False
    start_position_ms: Optional[int] = None
    stop_saved: bool = False
    stop_position_ms: Optional[int] = None
    trim_us: int = 0
    wifi_mode: str = "AP"
    ip_address: str = ""
    speed_percent: int = 50
    raw_response: str = ""


class DropCylinderManager:
    """
    Manages communication with the ESP32 drop cylinder controller.
    Supports both WiFi/TCP and USB serial connections.
    """

    DEFAULT_PORT = 8080
    DEFAULT_BAUDRATE = 115200
    POLL_INTERVAL = 0.2  # 200ms between status polls

    def __init__(self):
        # Connection mode and transports
        self._mode: Optional[ConnectionMode] = None
        self._socket: Optional[socket.socket] = None
        self._serial: Optional['serial.Serial'] = None
        self._state = DropCylinderConnectionState.DISCONNECTED

        # Connection details
        self._ip_address = ""
        self._port = self.DEFAULT_PORT
        self._serial_port = ""
        self._baudrate = self.DEFAULT_BAUDRATE

        # Threading
        self._read_thread: Optional[threading.Thread] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Command queue
        self._command_queue: queue.Queue = queue.Queue()

        # Callbacks
        self._status_callback: Optional[Callable[[DropCylinderStatus], None]] = None
        self._connection_callback: Optional[Callable[[DropCylinderConnectionState, str], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None

        # Last status
        self._last_status: Optional[DropCylinderStatus] = None
        self._last_response_time: float = 0

    @property
    def state(self) -> DropCylinderConnectionState:
        return self._state

    @property
    def mode(self) -> Optional[ConnectionMode]:
        return self._mode

    @property
    def is_connected(self) -> bool:
        return self._state == DropCylinderConnectionState.CONNECTED

    @property
    def last_status(self) -> Optional[DropCylinderStatus]:
        return self._last_status

    def set_status_callback(self, callback: Callable[[DropCylinderStatus], None]) -> None:
        self._status_callback = callback

    def set_connection_callback(self, callback: Callable[[DropCylinderConnectionState, str], None]) -> None:
        self._connection_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        self._error_callback = callback

    def _set_state(self, state: DropCylinderConnectionState, message: str = "") -> None:
        self._state = state
        if self._connection_callback:
            self._connection_callback(state, message)

    @staticmethod
    def list_serial_ports() -> List[str]:
        """List available serial ports for drop cylinder connection."""
        if not SERIAL_AVAILABLE:
            return []
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return sorted(ports)

    def connect(self, ip_address: str, port: int = 8080) -> bool:
        """Connect via WiFi/TCP (backward compatible method)."""
        return self.connect_wifi(ip_address, port)

    def connect_wifi(self, ip_address: str, port: int = 8080) -> bool:
        """Connect to the ESP32 drop cylinder controller via WiFi/TCP."""
        if self.is_connected:
            self.disconnect()

        self._mode = ConnectionMode.WIFI
        self._ip_address = ip_address
        self._port = port
        self._set_state(DropCylinderConnectionState.CONNECTING, f"Connecting to {ip_address}:{port}...")

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((ip_address, port))
            self._socket.settimeout(0.1)

            # Start background threads
            self._stop_event.clear()

            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()

            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()

            self._set_state(DropCylinderConnectionState.CONNECTED, f"Connected to {ip_address}")
            return True

        except socket.error as e:
            self._mode = None
            self._set_state(DropCylinderConnectionState.ERROR, str(e))
            if self._error_callback:
                self._error_callback(f"Connection failed: {e}")
            return False

    def connect_serial(self, port: str, baudrate: int = 115200) -> bool:
        """Connect to the ESP32 drop cylinder controller via USB serial."""
        if not SERIAL_AVAILABLE:
            self._set_state(DropCylinderConnectionState.ERROR, "pyserial not installed")
            if self._error_callback:
                self._error_callback("Serial support requires pyserial: pip install pyserial")
            return False

        if self.is_connected:
            self.disconnect()

        self._mode = ConnectionMode.SERIAL
        self._serial_port = port
        self._baudrate = baudrate
        self._set_state(DropCylinderConnectionState.CONNECTING, f"Connecting to {port}...")

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=0.1,
                write_timeout=1.0
            )

            # Start background threads
            self._stop_event.clear()

            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()

            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()

            self._set_state(DropCylinderConnectionState.CONNECTED, f"Connected to {port}")
            return True

        except serial.SerialException as e:
            self._mode = None
            self._set_state(DropCylinderConnectionState.ERROR, str(e))
            if self._error_callback:
                self._error_callback(f"Serial connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the ESP32 (works for both WiFi and serial)."""
        self._stop_event.set()

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=1.0)
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)

        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None

            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

        self._mode = None
        self._last_status = None
        self._set_state(DropCylinderConnectionState.DISCONNECTED, "Disconnected")

    def send_command(self, command: str) -> bool:
        """Send a command to the ESP32."""
        if not self.is_connected:
            return False
        self._command_queue.put(command)
        return True

    def _send_command_direct(self, command: str) -> bool:
        """Send command directly (from worker thread)."""
        with self._lock:
            data = (command.strip() + "\n").encode('ascii')

            if self._mode == ConnectionMode.WIFI:
                if not self._socket:
                    return False
                try:
                    self._socket.sendall(data)
                    return True
                except socket.error as e:
                    if self._error_callback:
                        self._error_callback(f"Send failed: {e}")
                    return False

            elif self._mode == ConnectionMode.SERIAL:
                if not self._serial or not self._serial.is_open:
                    return False
                try:
                    self._serial.write(data)
                    return True
                except serial.SerialException as e:
                    if self._error_callback:
                        self._error_callback(f"Send failed: {e}")
                    return False

            return False

    def _read_loop(self) -> None:
        """Background thread for reading responses."""
        buffer = ""
        disconnected_by_error = False

        while not self._stop_event.is_set():
            # Process queued commands
            try:
                while True:
                    command = self._command_queue.get_nowait()
                    self._send_command_direct(command)
            except queue.Empty:
                pass

            # Read data based on connection mode
            with self._lock:
                if self._mode == ConnectionMode.WIFI:
                    if not self._socket:
                        break
                    try:
                        data = self._socket.recv(1024)
                        if data:
                            buffer += data.decode('ascii', errors='ignore')
                        else:
                            # Empty data means connection closed
                            disconnected_by_error = True
                            break
                    except socket.timeout:
                        pass
                    except socket.error:
                        disconnected_by_error = True
                        break

                elif self._mode == ConnectionMode.SERIAL:
                    if not self._serial or not self._serial.is_open:
                        break
                    try:
                        if self._serial.in_waiting > 0:
                            data = self._serial.read(self._serial.in_waiting)
                            if data:
                                buffer += data.decode('ascii', errors='ignore')
                    except serial.SerialException:
                        disconnected_by_error = True
                        break

                else:
                    # No valid mode, exit loop
                    break

            # Process complete lines
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line:
                    self._process_response(line)

            time.sleep(0.01)

        # If we exited due to error/disconnect (not user-initiated), notify
        if disconnected_by_error and not self._stop_event.is_set():
            self._handle_unexpected_disconnect()

    def _poll_loop(self) -> None:
        """Background thread for status polling."""
        while not self._stop_event.is_set():
            if self.is_connected:
                self._send_command_direct("?")
            self._stop_event.wait(self.POLL_INTERVAL)

    def _handle_unexpected_disconnect(self) -> None:
        """Handle unexpected disconnection (e.g., WiFi lost or serial unplugged)."""
        mode = self._mode
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None

            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

        self._mode = None
        self._last_status = None
        self._set_state(DropCylinderConnectionState.DISCONNECTED, "Connection lost")
        if self._error_callback:
            if mode == ConnectionMode.SERIAL:
                self._error_callback("Connection lost - Serial disconnected")
            else:
                self._error_callback("Connection lost - WiFi disconnected")

    def _process_response(self, response: str) -> None:
        """Process a response from the ESP32."""
        status = self._parse_status(response)
        if status:
            self._last_status = status
            self._last_response_time = time.time()
            if self._status_callback:
                self._status_callback(status)

    def _parse_status(self, response: str) -> Optional[DropCylinderStatus]:
        """Parse a status response."""
        if not response.startswith("POS:"):
            return None

        status = DropCylinderStatus(raw_response=response)

        try:
            parts = response.split()
            for part in parts:
                if part.startswith("POS:"):
                    status.position_ms = int(part[4:])
                elif part.startswith("MODE:"):
                    status.mode = part[5:]
                elif part.startswith("START:"):
                    val = part[6:]
                    if val.startswith("Y@"):
                        status.start_saved = True
                        status.start_position_ms = int(val[2:])
                    else:
                        status.start_saved = False
                elif part.startswith("STOP:"):
                    val = part[5:]
                    if val.startswith("Y@"):
                        status.stop_saved = True
                        status.stop_position_ms = int(val[2:])
                    else:
                        status.stop_saved = False
                elif part.startswith("TRIM:"):
                    status.trim_us = int(part[5:])
                elif part.startswith("WIFI:"):
                    status.wifi_mode = part[5:]
                elif part.startswith("IP:"):
                    status.ip_address = part[3:]
                elif part.startswith("SPEED:"):
                    status.speed_percent = int(part[6:])
        except (ValueError, IndexError):
            return None

        return status

    # Convenience methods

    def jog_down(self) -> bool:
        return self.send_command("JD")

    def jog_up(self) -> bool:
        return self.send_command("JU")

    def jog_stop(self) -> bool:
        return self.send_command("JS")

    def go_start(self) -> bool:
        return self.send_command("GS")

    def go_stop_position(self) -> bool:
        return self.send_command("GP")

    def save_start(self) -> bool:
        return self.send_command("SS")

    def save_stop(self) -> bool:
        return self.send_command("SP")

    def stop(self) -> bool:
        return self.send_command("ST")

    def zero_position(self) -> bool:
        return self.send_command("ZERO")

    def set_trim(self, offset_us: int) -> bool:
        return self.send_command(f"TR{offset_us}")

    def set_speed(self, percent: int) -> bool:
        return self.send_command(f"VS{percent}")

    def set_wifi_credentials(self, ssid: str, password: str) -> bool:
        return self.send_command(f"WIFI:{ssid}:{password}")

    def clear_wifi_credentials(self) -> bool:
        return self.send_command("WIFI_CLEAR")


# Backward compatibility alias
WifiManager = DropCylinderManager
