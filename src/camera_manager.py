"""
Camera Manager Module

Handles MJPEG stream reading and camera discovery for ESP32-CAM devices.
Provides a clean separation between camera communication and GUI display.
"""

import socket
import threading
import urllib.request
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from .config import (
    CAMERA_STREAM_PORT,
    CAMERA_CONTROL_PORT,
    CAMERA_CONNECT_TIMEOUT,
    CAMERA_READ_TIMEOUT,
    CAMERA_SCAN_TIMEOUT,
)


class CameraConnectionState(Enum):
    """Camera connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class CameraConfig:
    """Camera connection configuration."""
    ip: str
    stream_port: int = CAMERA_STREAM_PORT
    control_port: int = CAMERA_CONTROL_PORT

    @property
    def stream_url(self) -> str:
        """Get the MJPEG stream URL."""
        return f"http://{self.ip}:{self.stream_port}/stream"

    @property
    def control_url(self) -> str:
        """Get the control endpoint base URL."""
        return f"http://{self.ip}:{self.control_port}"

    @property
    def flash_url(self) -> str:
        """Get the flash toggle URL."""
        return f"{self.control_url}/flash"


class MJPEGStreamReader:
    """
    Reads MJPEG stream from ESP32-CAM and provides frames via callback.
    Runs in a background thread.
    """

    # Maximum buffer size before forced cleanup (500KB)
    MAX_BUFFER_SIZE = 500000

    # Minimum valid JPEG frame size
    MIN_FRAME_SIZE = 100

    def __init__(
        self,
        url: str,
        on_frame: Callable[[bytes], None],
        on_error: Callable[[str], None]
    ):
        """
        Initialize the stream reader.

        Args:
            url: MJPEG stream URL
            on_frame: Callback for each received frame (JPEG bytes)
            on_error: Callback for errors
        """
        self._url = url
        self._on_frame = on_frame
        self._on_error = on_error
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        """Check if the stream reader is running."""
        return self._running

    def start(self) -> None:
        """Start reading the stream."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._read_stream, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop reading the stream."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _read_stream(self) -> None:
        """Read MJPEG stream and extract frames using raw socket."""
        sock = None
        try:
            host, port, path = self._parse_url(self._url)

            # Connect with socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CAMERA_CONNECT_TIMEOUT)
            sock.connect((host, port))

            # Send HTTP request
            request = f'GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: keep-alive\r\n\r\n'
            sock.send(request.encode())

            # Set longer timeout for reading stream
            sock.settimeout(CAMERA_READ_TIMEOUT)

            buffer = b''
            headers_done = False

            while self._running:
                try:
                    chunk = sock.recv(8192)
                    if not chunk:
                        break

                    buffer += chunk

                    # Skip HTTP headers on first read
                    if not headers_done:
                        header_end = buffer.find(b'\r\n\r\n')
                        if header_end != -1:
                            buffer = buffer[header_end + 4:]
                            headers_done = True
                        continue

                    # Extract JPEG frames from buffer
                    buffer = self._extract_frames(buffer)

                except socket.timeout:
                    # Timeout on recv is OK, just continue
                    continue

        except socket.timeout:
            if self._running:
                self._on_error("Connection timed out")
        except ConnectionRefusedError:
            if self._running:
                self._on_error("Connection refused - is the camera on?")
        except Exception as e:
            if self._running:
                self._on_error(f"Stream error: {str(e)}")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _parse_url(self, url: str) -> tuple:
        """
        Parse URL into host, port, and path components.

        Args:
            url: Full URL string

        Returns:
            Tuple of (host, port, path)
        """
        # Strip protocol
        if url.startswith('http://'):
            url = url[7:]

        # Split host:port from path
        if '/' in url:
            host_port, path = url.split('/', 1)
            path = '/' + path
        else:
            host_port = url
            path = '/stream'

        # Split host from port
        if ':' in host_port:
            host, port_str = host_port.split(':')
            port = int(port_str)
        else:
            host = host_port
            port = 80

        return host, port, path

    def _extract_frames(self, buffer: bytes) -> bytes:
        """
        Extract complete JPEG frames from buffer and invoke callback.

        Args:
            buffer: Current data buffer

        Returns:
            Remaining buffer after extracting frames
        """
        while True:
            # Find start of JPEG (SOI marker)
            jpg_start = buffer.find(b'\xff\xd8')
            if jpg_start == -1:
                # Keep last 2 bytes in case we're mid-marker
                if len(buffer) > 2:
                    buffer = buffer[-2:]
                break

            # Find end of JPEG (EOI marker)
            jpg_end = buffer.find(b'\xff\xd9', jpg_start)
            if jpg_end == -1:
                # Need more data, but don't let buffer grow too large
                if len(buffer) > self.MAX_BUFFER_SIZE:
                    buffer = buffer[-2:]
                break

            # Extract complete JPEG (include the EOI marker)
            jpg_end += 2
            frame_data = buffer[jpg_start:jpg_end]
            buffer = buffer[jpg_end:]

            # Deliver frame if valid
            if self._running and len(frame_data) > self.MIN_FRAME_SIZE:
                self._on_frame(frame_data)

        return buffer


class RTSPStreamReader:
    """
    Reads RTSP stream (e.g. from TAPO cameras) using OpenCV and provides
    JPEG frames via callback. Same interface as MJPEGStreamReader.

    Optimized for low latency:
    - Uses TCP transport for reliability
    - Minimal buffer size to reduce delay
    - Grabs frames without decoding, then retrieves only the latest
    """

    def __init__(
        self,
        url: str,
        on_frame: Callable[[bytes], None],
        on_error: Callable[[str], None]
    ):
        self._url = url
        self._on_frame = on_frame
        self._on_error = on_error
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_stream, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def _read_stream(self) -> None:
        try:
            import cv2
        except ImportError:
            if self._running:
                self._on_error("OpenCV not installed. Run: pip install opencv-python")
            return

        cap = None
        try:
            # Configure for low latency
            cap = cv2.VideoCapture(self._url, cv2.CAP_FFMPEG)

            # Minimal buffer - only keep 1 frame
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Use TCP transport (more reliable, often lower latency than UDP)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

            if not cap.isOpened():
                if self._running:
                    self._on_error("Could not open RTSP stream")
                return

            while self._running:
                # Grab multiple frames to clear buffer, keep only latest
                # This prevents lag buildup from buffered frames
                for _ in range(2):
                    cap.grab()

                # Now retrieve the latest frame
                ret, frame = cap.retrieve()
                if not ret:
                    # Try a regular read as fallback
                    ret, frame = cap.read()
                    if not ret:
                        if self._running:
                            self._on_error("Stream lost - no frame received")
                        break

                # Encode with lower quality for speed (80% quality)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
                _, jpeg = cv2.imencode('.jpg', frame, encode_params)
                if self._running:
                    self._on_frame(jpeg.tobytes())

        except Exception as e:
            if self._running:
                self._on_error(f"RTSP error: {str(e)}")
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass


class CameraDiscovery:
    """Auto-discover ESP32-CAM devices on the local network."""

    @staticmethod
    def get_local_ip() -> Optional[str]:
        """
        Get the local IP address of this machine.

        Returns:
            Local IP address or None if unable to determine
        """
        try:
            # Create a dummy connection to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    @staticmethod
    def scan_subnet(
        base_ip: str,
        on_found: Callable[[str], None],
        on_complete: Callable[[], None],
        on_progress: Optional[Callable[[int], None]] = None
    ) -> threading.Thread:
        """
        Scan local subnet for ESP32-CAM devices.

        Args:
            base_ip: IP address to derive subnet from (e.g., "192.168.1.100")
            on_found: Callback when a camera is found (receives IP)
            on_complete: Callback when scan is complete
            on_progress: Optional callback for progress updates (receives count 1-254)

        Returns:
            The scanning thread (for cancellation if needed)
        """
        def scan():
            # Extract subnet from base IP
            parts = base_ip.split('.')
            if len(parts) != 4:
                on_complete()
                return

            subnet = '.'.join(parts[:3])

            for i in range(1, 255):
                if on_progress:
                    on_progress(i)

                ip = f"{subnet}.{i}"
                if CameraDiscovery.check_camera(ip):
                    on_found(ip)

            on_complete()

        thread = threading.Thread(target=scan, daemon=True)
        thread.start()
        return thread

    @staticmethod
    def check_camera(ip: str, timeout: float = CAMERA_SCAN_TIMEOUT) -> bool:
        """
        Check if an IP address has an ESP32-CAM stream port open.

        Args:
            ip: IP address to check
            timeout: Connection timeout in seconds

        Returns:
            True if the stream port is open, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, CAMERA_STREAM_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False


class CameraController:
    """
    High-level controller for a single ESP32-CAM.
    Combines stream reading with camera control operations.
    """

    def __init__(self, config: CameraConfig):
        """
        Initialize the camera controller.

        Args:
            config: Camera configuration
        """
        self._config = config
        self._stream_reader: Optional[MJPEGStreamReader] = None
        self._state = CameraConnectionState.DISCONNECTED
        self._flash_on = False

        # Callbacks
        self._on_frame: Optional[Callable[[bytes], None]] = None
        self._on_state_change: Optional[Callable[[CameraConnectionState], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    @property
    def config(self) -> CameraConfig:
        """Get the camera configuration."""
        return self._config

    @property
    def state(self) -> CameraConnectionState:
        """Get the current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected and streaming."""
        return self._state == CameraConnectionState.CONNECTED

    @property
    def flash_on(self) -> bool:
        """Check if flash is on."""
        return self._flash_on

    def set_frame_callback(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for received frames."""
        self._on_frame = callback

    def set_state_callback(self, callback: Callable[[CameraConnectionState], None]) -> None:
        """Set callback for state changes."""
        self._on_state_change = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for errors."""
        self._on_error = callback

    def _set_state(self, state: CameraConnectionState) -> None:
        """Update state and notify callback."""
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def connect(self) -> None:
        """Start streaming from the camera."""
        if self._stream_reader and self._stream_reader.is_running:
            return

        self._set_state(CameraConnectionState.CONNECTING)

        def on_frame(data: bytes):
            # First frame received means we're connected
            if self._state != CameraConnectionState.CONNECTED:
                self._set_state(CameraConnectionState.CONNECTED)
            if self._on_frame:
                self._on_frame(data)

        def on_error(error: str):
            self._set_state(CameraConnectionState.ERROR)
            if self._on_error:
                self._on_error(error)

        self._stream_reader = MJPEGStreamReader(
            self._config.stream_url,
            on_frame=on_frame,
            on_error=on_error
        )
        self._stream_reader.start()

    def disconnect(self) -> None:
        """Stop streaming from the camera."""
        if self._stream_reader:
            self._stream_reader.stop()
            self._stream_reader = None

        self._flash_on = False
        self._set_state(CameraConnectionState.DISCONNECTED)

    def toggle_flash(self, callback: Optional[Callable[[bool], None]] = None) -> None:
        """
        Toggle the camera flash LED.

        Args:
            callback: Optional callback with new flash state
        """
        def send_flash():
            try:
                with urllib.request.urlopen(self._config.flash_url, timeout=5) as response:
                    result = response.read().decode()
                    self._flash_on = 'ON' in result
                    if callback:
                        callback(self._flash_on)
            except Exception as e:
                if self._on_error:
                    self._on_error(f"Flash control error: {e}")

        threading.Thread(target=send_flash, daemon=True).start()

    def set_flash(self, on: bool, callback: Optional[Callable[[bool], None]] = None) -> None:
        """
        Set the camera flash to a specific state.

        Args:
            on: True to turn flash on, False to turn off
            callback: Optional callback with resulting flash state
        """
        # If already in desired state, just callback
        if self._flash_on == on:
            if callback:
                callback(on)
            return

        # Toggle to change state
        self.toggle_flash(callback)
