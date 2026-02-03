#!/usr/bin/env python3
"""
Pulley Controller - Raspberry Pi Service

This script runs on the Raspberry Pi and:
1. Listens for commands from the laptop (TCP port 8081)
2. Translates them to SCL commands
3. Sends them to the STAC5 motor controller (192.168.0.40:7776)
4. Returns status/responses back to the laptop

Usage:
    python3 pulley_controller.py

The service will start automatically and listen for connections.
"""

import socket
import threading
import time
import sys

# =============================================================================
# Configuration
# =============================================================================

# STAC5 Motor Controller (Ethernet)
STAC5_HOST = "192.168.0.40"
STAC5_PORT = 7776

# Server for laptop connections (WiFi)
SERVER_HOST = "0.0.0.0"  # Listen on all interfaces
SERVER_PORT = 8081

# Motion defaults
DEFAULT_JOG_VELOCITY = 2.0      # rev/sec
DEFAULT_MOVE_VELOCITY = 1.5     # rev/sec
DEFAULT_ACCELERATION = 10.0     # rev/sec^2
DEFAULT_DECELERATION = 10.0     # rev/sec^2
STEPS_PER_REV = 4000

# =============================================================================
# STAC5 Communication
# =============================================================================

class STAC5:
    """Handles communication with the STAC5 motor controller via SCL protocol."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.lock = threading.Lock()

        # State tracking
        self.jog_velocity = DEFAULT_JOG_VELOCITY
        self.move_velocity = DEFAULT_MOVE_VELOCITY
        self.acceleration = DEFAULT_ACCELERATION
        self.deceleration = DEFAULT_DECELERATION

        # Saved positions (in steps)
        self.home_position = None
        self.well_position = None

    def connect(self):
        """Connect to the STAC5 controller."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[STAC5] Connected to {self.host}:{self.port}")

            # Initialize drive settings
            self._init_drive()
            return True

        except Exception as e:
            print(f"[STAC5] Connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from the STAC5 controller."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        print("[STAC5] Disconnected")

    def _init_drive(self):
        """Initialize drive with default settings."""
        self.send_command(f"AC{self.acceleration}")  # Acceleration
        self.send_command(f"DE{self.deceleration}")  # Deceleration
        self.send_command("ME")  # Motor Enable

    def send_command(self, cmd):
        """Send an SCL command and get response."""
        if not self.connected:
            return None

        with self.lock:
            try:
                # SCL commands end with carriage return
                full_cmd = cmd + "\r"
                self.socket.sendall(full_cmd.encode('ascii'))

                # Read response (with timeout)
                self.socket.settimeout(1.0)
                response = ""
                while True:
                    try:
                        data = self.socket.recv(1024).decode('ascii')
                        if not data:
                            break
                        response += data
                        if '\r' in response or '%' in response or '?' in response:
                            break
                    except socket.timeout:
                        break

                response = response.strip()
                print(f"[STAC5] TX: {cmd} | RX: {response}")
                return response

            except Exception as e:
                print(f"[STAC5] Command error: {e}")
                self.connected = False
                return None

    def get_encoder_position(self):
        """Read current encoder position."""
        response = self.send_command("EP")
        if response:
            try:
                # Response format: "EP=12345" or just "12345"
                if "=" in response:
                    return int(response.split("=")[1])
                return int(response.replace("%", "").replace("?", "").strip())
            except:
                pass
        return None

    def get_alarm_status(self):
        """Read alarm status."""
        response = self.send_command("AL")
        return response

    def alarm_reset(self):
        """Clear any alarms."""
        return self.send_command("AR")

    def motor_enable(self):
        """Enable the motor."""
        return self.send_command("ME")

    def motor_disable(self):
        """Disable the motor."""
        return self.send_command("MD")

    def stop(self):
        """Stop motion immediately."""
        self.send_command("ST")

    def stop_kill(self):
        """Emergency stop."""
        self.send_command("SK")

    def jog_start(self, direction):
        """
        Start jogging in specified direction.
        direction: 1 = positive (toward well), -1 = negative (toward home)
        """
        velocity = self.jog_velocity * direction
        self.send_command(f"JS{velocity}")  # Set jog speed
        self.send_command("CJ")  # Commence jogging

    def jog_stop(self):
        """Stop jogging."""
        self.send_command("SJ")

    def move_to_position(self, target_steps):
        """Move to an absolute position."""
        current = self.get_encoder_position()
        if current is None:
            return False

        distance = target_steps - current
        if distance == 0:
            return True

        self.send_command(f"VE{self.move_velocity}")  # Set velocity
        self.send_command(f"DI{distance}")  # Set distance
        self.send_command("FL")  # Feed to length (execute move)
        return True

    def move_relative(self, steps):
        """Move relative number of steps."""
        self.send_command(f"VE{self.move_velocity}")
        self.send_command(f"DI{steps}")
        self.send_command("FL")

    def save_home(self):
        """Save current position as home."""
        pos = self.get_encoder_position()
        if pos is not None:
            self.home_position = pos
            print(f"[STAC5] Home saved at {pos}")
            return True
        return False

    def save_well(self):
        """Save current position as well."""
        pos = self.get_encoder_position()
        if pos is not None:
            self.well_position = pos
            print(f"[STAC5] Well saved at {pos}")
            return True
        return False

    def go_home(self):
        """Move to saved home position."""
        if self.home_position is not None:
            return self.move_to_position(self.home_position)
        return False

    def go_well(self):
        """Move to saved well position."""
        if self.well_position is not None:
            return self.move_to_position(self.well_position)
        return False

    def set_jog_velocity(self, rps):
        """Set jog velocity in rev/sec."""
        if 0.1 <= rps <= 20.0:
            self.jog_velocity = rps
            return True
        return False

    def set_move_velocity(self, rps):
        """Set move velocity in rev/sec."""
        if 0.1 <= rps <= 20.0:
            self.move_velocity = rps
            return True
        return False


# =============================================================================
# Client Handler
# =============================================================================

class ClientHandler:
    """Handles communication with a connected laptop client."""

    def __init__(self, client_socket, client_address, stac5):
        self.socket = client_socket
        self.address = client_address
        self.stac5 = stac5
        self.running = True

    def handle(self):
        """Main loop to handle client commands."""
        print(f"[CLIENT] Connected: {self.address}")

        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break

                buffer += data

                # Process complete commands (newline terminated)
                while '\n' in buffer or '\r' in buffer:
                    # Split on either newline type
                    for sep in ['\r\n', '\n', '\r']:
                        if sep in buffer:
                            cmd, buffer = buffer.split(sep, 1)
                            break

                    cmd = cmd.strip()
                    if cmd:
                        response = self.process_command(cmd)
                        if response:
                            self.socket.sendall((response + "\n").encode('utf-8'))

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[CLIENT] Error: {e}")
                break

        print(f"[CLIENT] Disconnected: {self.address}")
        self.socket.close()

    def process_command(self, cmd):
        """
        Process a command from the laptop.
        Returns response string.
        """
        cmd = cmd.upper().strip()
        print(f"[CLIENT] Command: {cmd}")

        # Status query
        if cmd == "?":
            return self.get_status()

        # Jog commands
        if cmd == "JL":  # Jog Left (toward home)
            self.stac5.jog_start(-1)
            return "OK"

        if cmd == "JR":  # Jog Right (toward well)
            self.stac5.jog_start(1)
            return "OK"

        if cmd == "JS":  # Jog Stop
            self.stac5.jog_stop()
            return "OK"

        # Position commands
        if cmd == "GH":  # Go Home
            if self.stac5.go_home():
                return "OK"
            return "ERR:NO_HOME"

        if cmd == "GW":  # Go Well
            if self.stac5.go_well():
                return "OK"
            return "ERR:NO_WELL"

        if cmd == "SH":  # Save Home
            if self.stac5.save_home():
                return "OK"
            return "ERR:SAVE_FAILED"

        if cmd == "SW":  # Save Well
            if self.stac5.save_well():
                return "OK"
            return "ERR:SAVE_FAILED"

        # Stop commands
        if cmd == "ST":  # Stop
            self.stac5.stop()
            return "OK"

        if cmd == "SK":  # Stop Kill (emergency)
            self.stac5.stop_kill()
            return "OK"

        # Go to absolute position: GT<steps>
        if cmd.startswith("GT"):
            try:
                pos = int(cmd[2:])
                self.stac5.move_to_position(pos)
                return "OK"
            except:
                return "ERR:INVALID_POS"

        # Move relative: MR<steps>
        if cmd.startswith("MR"):
            try:
                steps = int(cmd[2:])
                self.stac5.move_relative(steps)
                return "OK"
            except:
                return "ERR:INVALID_STEPS"

        # Set jog velocity: VJ<rps>
        if cmd.startswith("VJ"):
            try:
                rps = float(cmd[2:])
                if self.stac5.set_jog_velocity(rps):
                    return "OK"
                return "ERR:INVALID_VEL"
            except:
                return "ERR:INVALID_VEL"

        # Set move velocity: VM<rps>
        if cmd.startswith("VM"):
            try:
                rps = float(cmd[2:])
                if self.stac5.set_move_velocity(rps):
                    return "OK"
                return "ERR:INVALID_VEL"
            except:
                return "ERR:INVALID_VEL"

        # Alarm reset
        if cmd == "AR":
            self.stac5.alarm_reset()
            return "OK"

        # Motor enable/disable
        if cmd == "ME":
            self.stac5.motor_enable()
            return "OK"

        if cmd == "MD":
            self.stac5.motor_disable()
            return "OK"

        return "ERR:UNKNOWN_CMD"

    def get_status(self):
        """Build status response string."""
        pos = self.stac5.get_encoder_position()
        if pos is None:
            pos = 0

        # Format: POS:<steps> HOME:<Y@steps|N> WELL:<Y@steps|N> VJOG:<rps> VMOVE:<rps> CONN:<0|1>
        status = f"POS:{pos}"

        if self.stac5.home_position is not None:
            status += f" HOME:Y@{self.stac5.home_position}"
        else:
            status += " HOME:N"

        if self.stac5.well_position is not None:
            status += f" WELL:Y@{self.stac5.well_position}"
        else:
            status += " WELL:N"

        status += f" VJOG:{self.stac5.jog_velocity:.2f}"
        status += f" VMOVE:{self.stac5.move_velocity:.2f}"
        status += f" CONN:{'1' if self.stac5.connected else '0'}"

        return status

    def stop(self):
        """Stop the handler."""
        self.running = False


# =============================================================================
# Main Server
# =============================================================================

class PulleyServer:
    """Main server that manages connections."""

    def __init__(self):
        self.stac5 = STAC5(STAC5_HOST, STAC5_PORT)
        self.server_socket = None
        self.running = False
        self.clients = []

    def start(self):
        """Start the server."""
        print("=" * 50)
        print("Pulley Controller - Raspberry Pi")
        print("=" * 50)

        # Connect to STAC5
        print(f"\n[STAC5] Connecting to {STAC5_HOST}:{STAC5_PORT}...")
        if not self.stac5.connect():
            print("[STAC5] WARNING: Could not connect to STAC5")
            print("[STAC5] Server will start anyway - connect STAC5 and restart")

        # Start TCP server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((SERVER_HOST, SERVER_PORT))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)

        self.running = True

        print(f"\n[SERVER] Listening on port {SERVER_PORT}")
        print("[SERVER] Waiting for laptop connection...")
        print("\nPress Ctrl+C to stop\n")

        # Accept connections
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_socket.settimeout(1.0)

                # Handle client in new thread
                handler = ClientHandler(client_socket, client_address, self.stac5)
                thread = threading.Thread(target=handler.handle, daemon=True)
                thread.start()
                self.clients.append(handler)

            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[SERVER] Error: {e}")

        self.stop()

    def stop(self):
        """Stop the server."""
        print("\n[SERVER] Shutting down...")
        self.running = False

        # Stop all clients
        for client in self.clients:
            client.stop()

        # Close server socket
        if self.server_socket:
            self.server_socket.close()

        # Disconnect from STAC5
        self.stac5.disconnect()

        print("[SERVER] Stopped")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    server = PulleyServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
