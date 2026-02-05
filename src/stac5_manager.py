"""
STAC5 Motor Controller Manager

Handles direct TCP communication with the STAC5-IP stepper drive using eSCL protocol.
"""

import socket
import threading
import time
from typing import Optional, Callable, Tuple
from dataclasses import dataclass


# eSCL Protocol Constants
ESCL_HEADER = bytes([0x00, 0x07])
CARRIAGE_RETURN = bytes([0x0D])


@dataclass
class STAC5Status:
    """Status data from the STAC5 controller."""
    connected: bool = False
    encoder_position: int = 0
    alarm_code: str = "0000"
    status_code: str = "0000"
    is_moving: bool = False
    motor_enabled: bool = False
    home_position: Optional[int] = None
    well_position: Optional[int] = None
    jog_velocity: float = 2.0
    move_velocity: float = 1.5


class STAC5Manager:
    """
    Manages communication with STAC5 motor controller over Ethernet.

    Uses eSCL (SCL over Ethernet) protocol:
    - TCP port 7776
    - Packet format: [0x00, 0x07] + ASCII command + [0x0D]
    """

    def __init__(self, host: str = "192.168.1.40", port: int = 7776):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._connected = False

        # Status
        self.status = STAC5Status()

        # Polling
        self._poll_thread: Optional[threading.Thread] = None
        self._polling = False
        self._poll_interval = 0.15  # 150ms

        # Callbacks
        self._status_callback: Optional[Callable[[STAC5Status], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None

        # Motion defaults
        self.default_jog_velocity = 2.0    # rev/sec
        self.default_move_velocity = 1.5   # rev/sec
        self.default_acceleration = 10.0   # rev/sec^2
        self.default_deceleration = 10.0   # rev/sec^2

        # Electronic gearing ratio (EG/ER = 20000/8000 = 2.5)
        # Motor steps = encoder counts * gear_ratio
        self.gear_ratio = 2.5

        # Track when last move command was sent for fast polling
        self._last_move_time = 0.0

        # Rate limiting - minimum time between move commands (seconds)
        self._min_command_interval = 0.5  # 500ms between move commands
        self._last_move_command_time = 0.0

        # Jog state tracking
        self._jog_active = False  # True when jog is running
        self._jog_stop_time = 0.0  # When jog stop was sent
        self._jog_decel_lockout = 0.5  # Lockout period after jog stop (seconds)

    def set_status_callback(self, callback: Callable[[STAC5Status], None]):
        """Set callback for status updates."""
        self._status_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]):
        """Set callback for error notifications."""
        self._error_callback = callback

    def _notify_error(self, message: str):
        """Notify error via callback."""
        print(f"[STAC5] Error: {message}")
        if self._error_callback:
            self._error_callback(message)

    def _notify_status(self):
        """Notify status update via callback."""
        if self._status_callback:
            self._status_callback(self.status)

    def _decode_alarm(self, alarm_code: str) -> str:
        """Decode alarm code to human-readable message."""
        # STAC5 alarm codes (from Applied Motion documentation)
        alarm_messages = {
            "0000": "No Alarm",
            "0001": "Position Limit",
            "0002": "CCW Limit",
            "0004": "CW Limit",
            "0008": "Over Temp",
            "0010": "Internal Voltage",
            "0020": "Over Voltage",
            "0040": "Under Voltage",
            "0080": "Over Current",
            "0100": "Open Motor Winding",
            "0200": "Bad Encoder",
            "0400": "Comm Error",
            "0800": "Bad Flash",
            "1000": "No Move",
            "2000": "Blank Q Segment",
            "4000": "No Motor Connected",
            "8000": "Motor Disabled",
        }
        # Try exact match first
        if alarm_code in alarm_messages:
            return alarm_messages[alarm_code]
        # Try to decode as hex bitmask
        try:
            code = int(alarm_code, 16)
            if code == 0:
                return "No Alarm"
            # Check each bit
            alarms = []
            for hex_code, msg in alarm_messages.items():
                bit = int(hex_code, 16)
                if bit and (code & bit):
                    alarms.append(msg)
            return ", ".join(alarms) if alarms else f"Unknown ({alarm_code})"
        except:
            return f"Unknown ({alarm_code})"

    def _build_packet(self, command: str) -> bytes:
        """Build an eSCL packet for the given SCL command."""
        return ESCL_HEADER + command.encode('ascii') + CARRIAGE_RETURN

    def _parse_response(self, data: bytes) -> Optional[str]:
        """Parse an eSCL response packet."""
        if len(data) < 3:
            return None

        # Check header
        if data[0] != 0x00 or data[1] != 0x07:
            # Some responses might not have header
            return data.decode('ascii', errors='replace').strip()

        # Extract the response (skip header, remove CR)
        response = data[2:].decode('ascii', errors='replace').strip()
        return response

    def connect(self) -> bool:
        """Connect to the STAC5 controller."""
        # Clean up any previous connection
        if self._connected or self.socket:
            print("[STAC5] Cleaning up previous connection...")
            self.disconnect()

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self._connected = True
            self.status.connected = True
            print(f"[STAC5] Connected to {self.host}:{self.port}")

            # Initialize drive settings
            self._init_drive()

            return True

        except Exception as e:
            self._notify_error(f"Connection failed: {e}")
            self._connected = False
            self.status.connected = False
            return False

    def disconnect(self):
        """Disconnect from the STAC5 controller."""
        self.stop_polling()

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
        self._connected = False
        # Reset all status flags
        self.status.connected = False
        self.status.is_moving = False
        self.status.motor_enabled = False
        self.status.alarm_code = "0000"
        self.status.status_code = "0000"
        self.status.encoder_position = 0
        print("[STAC5] Disconnected")

    def is_connected(self) -> bool:
        """Check if connected to STAC5."""
        return self._connected

    def _init_drive(self):
        """Initialize drive with default settings."""
        self.send_command(f"AC{self.default_acceleration:.1f}")  # Acceleration
        self.send_command(f"DE{self.default_deceleration:.1f}")  # Deceleration
        self.send_command("ME")  # Motor Enable
        self.status.motor_enabled = True

        # Sync internal position (SP) to encoder position (EP)
        # This is required for FP (Feed to Position) to work correctly
        self._sync_positions()

        # Note: Network watchdog commands (ZS, ZE, ZA) are not supported on
        # the STAC5-IP-E120. Safety is provided by using incremental jogging
        # (small FL moves) instead of continuous jogging. If communication
        # fails, motor only travels one small increment before stopping.

    def _encoder_to_motor(self, encoder_counts: int) -> int:
        """Convert encoder counts to motor steps using gear ratio."""
        return int(encoder_counts * self.gear_ratio)

    def _sync_positions(self):
        """Sync internal step position (SP) to encoder position (EP)."""
        ep = self.get_encoder_position()
        if ep is not None:
            motor_steps = self._encoder_to_motor(ep)
            self.send_command(f"SP{motor_steps}")
            print(f"[STAC5] Synced SP to EP: encoder={ep}, motor={motor_steps}")

    def send_command(self, command: str, timeout: float = 1.0) -> Optional[str]:
        """
        Send an SCL command and get response.

        Args:
            command: SCL command string (e.g., "RV", "ME", "EP")
            timeout: Response timeout in seconds

        Returns:
            Response string, or None if failed
        """
        if not self._connected or not self.socket:
            return None

        with self._lock:
            try:
                # Clear any pending data in receive buffer first
                self.socket.setblocking(False)
                try:
                    while True:
                        self.socket.recv(1024)
                except:
                    pass
                self.socket.setblocking(True)

                # Build and send packet
                packet = self._build_packet(command)
                self.socket.sendall(packet)

                # Small delay to let response arrive
                time.sleep(0.01)  # Reduced from 50ms to 10ms for faster polling

                # Read response
                self.socket.settimeout(timeout)
                response_data = b""

                while True:
                    try:
                        data = self.socket.recv(1024)
                        if not data:
                            break
                        response_data += data
                        # Check for response terminators
                        if b'\r' in response_data or b'%' in response_data or b'?' in response_data:
                            break
                    except socket.timeout:
                        break

                response = self._parse_response(response_data)
                print(f"[STAC5] TX: {command} | RX: {response}")
                return response

            except Exception as e:
                self._notify_error(f"Command failed: {e}")
                self._connected = False
                self.status.connected = False
                return None

    # =========================================================================
    # Status Commands
    # =========================================================================

    def get_encoder_position(self) -> Optional[int]:
        """Read current encoder position (use when drive is idle)."""
        response = self.send_command("EP")
        if response:
            try:
                # Response format: "EP=12345" or "EP=12345 EP=12345" (duplicated)
                # Find first EP= and extract the number after it
                if "EP=" in response:
                    idx = response.find("EP=") + 3
                    end = idx
                    # Extract digits and minus sign
                    while end < len(response) and (response[end].isdigit() or response[end] == '-'):
                        end += 1
                    return int(response[idx:end])
                else:
                    # Fallback: try to parse cleaned response
                    clean = response.replace("=", "").replace("EP", "")
                    clean = clean.replace("%", "").replace("?", "").replace("*", "").strip()
                    # Take first number if multiple
                    parts = clean.split()
                    if parts:
                        return int(parts[0])
            except ValueError:
                pass
        return None

    def get_immediate_encoder(self) -> Optional[int]:
        """Read encoder position using Immediate Encoder command (works during motion)."""
        response = self.send_command("IE")
        if response:
            try:
                # Response format: "IE=12345"
                if "IE=" in response:
                    idx = response.find("IE=") + 3
                    end = idx
                    while end < len(response) and (response[end].isdigit() or response[end] == '-'):
                        end += 1
                    return int(response[idx:end])
                else:
                    clean = response.replace("=", "").replace("IE", "")
                    clean = clean.replace("%", "").replace("?", "").replace("*", "").strip()
                    parts = clean.split()
                    if parts:
                        return int(parts[0])
            except ValueError:
                pass
        return None

    def get_alarm_code(self) -> Optional[str]:
        """Read alarm status."""
        response = self.send_command("AL")
        if response:
            clean = response.replace("=", "").replace("AL", "")
            clean = clean.replace("%", "").replace("?", "").replace("*", "").strip()
            return clean
        return None

    def get_status_code(self) -> Optional[str]:
        """Read drive status code."""
        response = self.send_command("SC")
        if response:
            # Response format: "SC=0001" or duplicated
            if "SC=" in response:
                idx = response.find("SC=") + 3
                end = idx
                while end < len(response) and response[end].isalnum():
                    end += 1
                return response[idx:end]
            else:
                clean = response.replace("=", "").replace("SC", "")
                clean = clean.replace("%", "").replace("?", "").replace("*", "").strip()
                parts = clean.split()
                if parts:
                    return parts[0]
        return None

    def get_immediate_velocity(self) -> Optional[float]:
        """Read current velocity."""
        response = self.send_command("IV")
        if response:
            try:
                clean = response.replace("=", "").replace("IV", "")
                clean = clean.replace("%", "").replace("?", "").replace("*", "").strip()
                return float(clean)
            except ValueError:
                pass
        return None

    # =========================================================================
    # Motor Control Commands
    # =========================================================================

    def motor_enable(self) -> bool:
        """Enable the motor."""
        response = self.send_command("ME")
        if response is not None:
            self.status.motor_enabled = True
            return True
        return False

    def motor_disable(self) -> bool:
        """Disable the motor."""
        response = self.send_command("MD")
        if response is not None:
            self.status.motor_enabled = False
            return True
        return False

    def alarm_reset(self) -> bool:
        """Clear any alarms."""
        old_alarm = self.status.alarm_code
        response = self.send_command("AR")
        if response is not None:
            print(f"[STAC5] Alarm reset sent (was: {old_alarm})")
            self.status.alarm_code = "0000"
            return True
        return False

    def stop(self) -> bool:
        """Stop motion (controlled deceleration)."""
        response = self.send_command("ST")
        self._jog_active = False
        self._jog_stop_time = time.time()  # Start lockout period
        self.status.is_moving = False
        return response is not None

    def stop_kill(self) -> bool:
        """Emergency stop (immediate)."""
        response = self.send_command("SK")
        self._jog_active = False
        self._jog_stop_time = time.time()
        self.status.is_moving = False
        return response is not None

    # =========================================================================
    # Jog Commands (DI-based direction control)
    # =========================================================================

    def jog_start(self, direction: int) -> bool:
        """
        Start jogging in specified direction.

        Uses DI command to set direction before CJ, since SD (Set Direction)
        is not supported on STAC5-IP-E120. DI1 or DI-1 sets the internal
        direction flag that CJ then uses.

        Args:
            direction: 1 = positive (CW), -1 = negative (CCW)
        """
        # Don't start if already jogging
        if self._jog_active:
            print("[STAC5] Jog start ignored - already jogging")
            return False

        # Lockout period after jog stop to allow deceleration
        now = time.time()
        time_since_stop = now - self._jog_stop_time
        if time_since_stop < self._jog_decel_lockout:
            print(f"[STAC5] Jog start ignored - lockout ({time_since_stop:.2f}s < {self._jog_decel_lockout}s)")
            return False

        # Mark as active BEFORE sending commands to prevent race conditions
        self._jog_active = True

        # Set direction using DI command (DI1 = positive, DI-1 = negative)
        dir_cmd = "DI1" if direction >= 0 else "DI-1"
        self.send_command(dir_cmd)

        # Set jog speed
        self.send_command(f"JS{self.status.jog_velocity:.1f}")

        # Commence jogging
        response = self.send_command("CJ")
        if response is not None:
            self.status.is_moving = True
            self._last_move_time = time.time()  # Trigger fast polling
            return True
        else:
            # Failed to start, reset state
            self._jog_active = False
            return False

    def jog_stop(self) -> bool:
        """Stop jogging (decelerate to stop)."""
        # Clear state FIRST to prevent any race conditions
        self._jog_active = False
        self._jog_stop_time = time.time()
        self.status.is_moving = False

        # Send SJ to decelerate to stop (don't use ST - that's immediate stop)
        self.send_command("SJ")

        return True

    def set_jog_velocity(self, rps: float) -> bool:
        """Set jog velocity in rev/sec."""
        if 0.1 <= rps <= 20.0:
            self.status.jog_velocity = rps
            return True
        return False

    # =========================================================================
    # Move Commands
    # =========================================================================

    def move_relative(self, steps: int) -> bool:
        """Move relative number of steps."""
        # Rate limiting - ignore if command sent too recently
        now = time.time()
        if now - self._last_move_command_time < self._min_command_interval:
            print(f"[STAC5] Move command ignored - rate limited ({self._min_command_interval}s)")
            return False
        self._last_move_command_time = now

        # Set velocity (always positive, with decimal point for compatibility)
        self.send_command(f"VE{self.status.move_velocity:.1f}")

        # Set distance (signed value - DI accepts positive and negative)
        self.send_command(f"DI{steps}")

        # Feed to length (execute move)
        response = self.send_command("FL")
        if response is not None:
            self.status.is_moving = True
            self._last_move_time = time.time()  # Trigger fast polling
            return True
        return False

    def move_to_position(self, target_steps: int) -> bool:
        """Move to an absolute encoder position using FP command."""
        # Rate limiting - ignore if command sent too recently
        now = time.time()
        if now - self._last_move_command_time < self._min_command_interval:
            print(f"[STAC5] Move command ignored - rate limited ({self._min_command_interval}s)")
            return False
        self._last_move_command_time = now

        # Stop any current motion before starting new move
        if self.status.is_moving:
            print("[STAC5] Stopping current motion before new move")
            self.send_command("ST")
            time.sleep(0.05)  # Brief pause for stop to take effect

        current = self.get_encoder_position()
        print(f"[STAC5] Move to position: target={target_steps}, current={current}")

        if current is not None and current == target_steps:
            print("[STAC5] Already at target position")
            return True

        # Sync SP to current encoder position (scaled to motor steps)
        self._sync_positions()

        # Convert target encoder position to motor steps
        target_motor = self._encoder_to_motor(target_steps)

        # Set velocity
        self.send_command(f"VE{self.status.move_velocity:.1f}")

        # Use FP (Feed to Position) for absolute positioning in motor steps
        response = self.send_command(f"FP{target_motor}")
        print(f"[STAC5] FP{target_motor} (encoder target: {target_steps}) response: {response}")

        if response is not None:
            self.status.is_moving = True
            self._last_move_time = time.time()  # Trigger fast polling
            return True
        return False

    def set_move_velocity(self, rps: float) -> bool:
        """Set move velocity in rev/sec."""
        if 0.1 <= rps <= 20.0:
            self.status.move_velocity = rps
            return True
        return False

    # =========================================================================
    # Position Memory
    # =========================================================================

    def save_home(self) -> bool:
        """Save current position as home."""
        pos = self.get_encoder_position()
        if pos is not None:
            self.status.home_position = pos
            print(f"[STAC5] Home saved at {pos}")
            return True
        return False

    def save_well(self) -> bool:
        """Save current position as well."""
        pos = self.get_encoder_position()
        if pos is not None:
            self.status.well_position = pos
            print(f"[STAC5] Well saved at {pos}")
            return True
        return False

    def go_home(self) -> bool:
        """Move to saved home position."""
        print(f"[STAC5] Go Home called - saved position: {self.status.home_position}")
        if self.status.home_position is not None:
            return self.move_to_position(self.status.home_position)
        print("[STAC5] Go Home failed - no home position saved")
        return False

    def go_well(self) -> bool:
        """Move to saved well position."""
        print(f"[STAC5] Go Well called - saved position: {self.status.well_position}")
        if self.status.well_position is not None:
            return self.move_to_position(self.status.well_position)
        print("[STAC5] Go Well failed - no well position saved")
        return False

    def zero_encoder(self) -> bool:
        """Zero the encoder position (set current position as 0)."""
        response = self.send_command("EP0")
        if response is not None:
            self.status.encoder_position = 0
            print("[STAC5] Encoder zeroed")
            return True
        return False

    # =========================================================================
    # Status Polling
    # =========================================================================

    def start_polling(self, interval: float = 0.15):
        """Start polling for status updates."""
        # Make sure any previous polling is fully stopped
        if self._polling or self._poll_thread is not None:
            print("[STAC5] Stopping previous polling before starting new...")
            self.stop_polling()

        self._poll_interval = interval
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        print(f"[STAC5] Started polling (interval: {interval}s)")

    def stop_polling(self):
        """Stop polling for status updates."""
        self._polling = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            if self._poll_thread.is_alive():
                print("[STAC5] Warning: Poll thread did not stop cleanly")
            self._poll_thread = None
        print("[STAC5] Stopped polling")

    def _poll_loop(self):
        """Background polling loop."""
        last_alarm = "0000"  # Track last alarm to detect new faults
        full_poll_counter = 0  # Counter for full status polls
        print("[STAC5] Poll loop started")

        while self._polling and self._connected:
            # Check if we should be in fast polling mode
            # Fast mode when: is_moving flag is set OR a move was started recently (within 3 seconds)
            time_since_move = time.time() - self._last_move_time
            in_motion_mode = self.status.is_moving or time_since_move < 3.0

            try:
                # Read encoder position
                # Use IE (Immediate Encoder) during motion - it works while drive is busy
                # Use EP (Encoder Position) when idle - it's the standard command
                if in_motion_mode:
                    pos = self.get_immediate_encoder()
                else:
                    pos = self.get_encoder_position()

                if pos is not None:
                    self.status.encoder_position = pos

                # Only read SC and AL every 5th cycle when in motion mode
                # Always read when idle for full status
                full_poll_counter += 1
                if full_poll_counter >= 5 or not in_motion_mode:
                    full_poll_counter = 0

                    # Read status code
                    sc = self.get_status_code()
                    if sc:
                        self.status.status_code = sc
                        try:
                            sc_int = int(sc, 16)
                            # Bit 0: Motor enabled
                            self.status.motor_enabled = bool(sc_int & 0x0001)
                            # Bit 4 (0x0010): Moving/In Motion
                            self.status.is_moving = bool(sc_int & 0x0010)
                        except:
                            pass

                    # Read alarm code and detect new faults
                    al = self.get_alarm_code()
                    if al:
                        self.status.alarm_code = al
                        # Check if this is a new fault (non-zero and different from last)
                        if al != "0000" and al != last_alarm:
                            fault_msg = self._decode_alarm(al)
                            print(f"[STAC5] FAULT DETECTED: {al} - {fault_msg}")
                            self._notify_error(f"FAULT {al}: {fault_msg}")
                        last_alarm = al

                # Notify callback
                self._notify_status()

            except Exception as e:
                print(f"[STAC5] Poll error: {e}")

            # Use shorter sleep when in motion mode for faster updates
            if in_motion_mode:
                time.sleep(0.03)  # 30ms when moving for ~30 updates/sec
            else:
                time.sleep(self._poll_interval)  # Normal interval when idle

        print(f"[STAC5] Poll loop exited (polling={self._polling}, connected={self._connected})")

    def poll_once(self) -> STAC5Status:
        """Poll status once (blocking)."""
        pos = self.get_encoder_position()
        if pos is not None:
            self.status.encoder_position = pos

        sc = self.get_status_code()
        if sc:
            self.status.status_code = sc

        al = self.get_alarm_code()
        if al:
            self.status.alarm_code = al

        return self.status
