"""
Main Application Window

Integrates all GUI components and handles keyboard shortcuts.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Set

from ..serial_manager import SerialManager, ConnectionState
from ..wifi_manager import DropCylinderManager, DropCylinderConnectionState, DropCylinderStatus, ConnectionMode
# Backward compatibility aliases
WifiManager = DropCylinderManager
WifiConnectionState = DropCylinderConnectionState
from ..command_protocol import WinchStatus
from .position_display import PositionDisplay
from .control_panel import ControlPanel
from .settings_panel import SettingsPanel
from .status_bar import StatusBar
from .settings_dialog import SettingsDialog
from .drop_cylinder_panel import DropCylinderPanel


class MainWindow:
    """
    Main application window for the Winch Control application.

    Integrates:
    - Connection bar with port selection
    - Position display
    - Jog and motion controls
    - Settings panel
    - Status bar

    Handles keyboard shortcuts and GUI updates from serial thread.
    """

    WINDOW_TITLE = "Winch Control"
    WINDOW_MIN_WIDTH = 500
    WINDOW_MIN_HEIGHT = 480

    # Default baud rates
    BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400]
    DEFAULT_BAUD = 115200

    def __init__(self, root: tk.Tk):
        self._root = root
        self._serial_manager = SerialManager()
        self._drop_cylinder_manager = DropCylinderManager()

        # Track pressed keys for jog
        self._pressed_keys: Set[str] = set()

        # Track if we've shown a drop cylinder error (to avoid spam)
        self._drop_error_shown = False

        # Setup window
        self._setup_window()
        self._create_widgets()
        self._setup_callbacks()
        self._setup_keyboard_bindings()

        # Initial state
        self._update_controls_state()
        self._refresh_ports()

    def _setup_window(self) -> None:
        """Configure the main window."""
        self._root.title(self.WINDOW_TITLE)
        self._root.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)
        self._root.columnconfigure(0, weight=1)

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Connection Bar
        self._create_connection_bar()

        # Separator
        ttk.Separator(self._root, orient=tk.HORIZONTAL).grid(
            row=1, column=0, sticky="ew", pady=2
        )

        # Position Display
        self._position_display = PositionDisplay(self._root)
        self._position_display.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

        # Control Panel
        self._control_panel = ControlPanel(
            self._root,
            on_jog_left_press=self._on_jog_left_press,
            on_jog_left_release=self._on_jog_left_release,
            on_jog_right_press=self._on_jog_right_press,
            on_jog_right_release=self._on_jog_right_release,
            on_go_home=self._on_go_home,
            on_go_well=self._on_go_well,
            on_stop=self._on_stop,
            on_go_to=self._on_go_to,
            on_move_relative=self._on_move_relative
        )
        self._control_panel.grid(row=3, column=0, sticky="ew", padx=5, pady=2)

        # Settings Panel
        self._settings_panel = SettingsPanel(
            self._root,
            on_save_home=self._on_save_home,
            on_save_well=self._on_save_well,
            on_zero_position=self._on_zero_position
        )
        self._settings_panel.grid(row=4, column=0, sticky="ew", padx=5, pady=2)

        # Drop Cylinder Panel
        self._drop_cylinder_panel = DropCylinderPanel(
            self._root,
            on_connect_wifi=self._on_drop_connect_wifi,
            on_connect_serial=self._on_drop_connect_serial,
            on_disconnect=self._on_drop_disconnect,
            on_refresh_ports=self._on_drop_refresh_ports,
            on_jog_down_press=self._on_drop_jog_down_press,
            on_jog_down_release=self._on_drop_jog_down_release,
            on_jog_up_press=self._on_drop_jog_up_press,
            on_jog_up_release=self._on_drop_jog_up_release,
            on_go_start=self._on_drop_go_start,
            on_go_stop=self._on_drop_go_stop,
            on_save_start=self._on_drop_save_start,
            on_save_stop=self._on_drop_save_stop,
            on_stop=self._on_drop_stop,
            on_set_trim=self._on_drop_set_trim,
            on_set_speed=self._on_drop_set_speed,
            on_configure_wifi=self._on_drop_configure_wifi,
            on_test=self._on_drop_test
        )
        self._drop_cylinder_panel.grid(row=5, column=0, sticky="ew", padx=5, pady=2)

        # Status Bar
        self._status_bar = StatusBar(self._root)
        self._status_bar.grid(row=6, column=0, sticky="ew", padx=5, pady=2)

    def _create_connection_bar(self) -> None:
        """Create the connection controls bar."""
        conn_frame = ttk.Frame(self._root)
        conn_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Port selection
        ttk.Label(conn_frame, text="Port:").pack(side=tk.LEFT, padx=(0, 3))

        self._port_var = tk.StringVar()
        self._port_combo = ttk.Combobox(
            conn_frame,
            textvariable=self._port_var,
            width=12,
            state="readonly"
        )
        self._port_combo.pack(side=tk.LEFT, padx=(0, 3))

        # Refresh ports button
        self._refresh_btn = ttk.Button(
            conn_frame,
            text="\u21BB",
            width=2,
            command=self._refresh_ports
        )
        self._refresh_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Baud rate selection
        ttk.Label(conn_frame, text="Baud:").pack(side=tk.LEFT, padx=(0, 3))

        self._baud_var = tk.StringVar(value=str(self.DEFAULT_BAUD))
        self._baud_combo = ttk.Combobox(
            conn_frame,
            textvariable=self._baud_var,
            values=[str(b) for b in self.BAUD_RATES],
            width=8,
            state="readonly"
        )
        self._baud_combo.pack(side=tk.LEFT, padx=(0, 8))

        # Connect/Disconnect button
        self._connect_btn = ttk.Button(
            conn_frame,
            text="Connect",
            command=self._toggle_connection,
            width=10
        )
        self._connect_btn.pack(side=tk.LEFT)

        # Settings button
        self._settings_btn = ttk.Button(
            conn_frame,
            text="\u2699",  # Gear icon
            command=self._open_settings,
            width=3
        )
        self._settings_btn.pack(side=tk.LEFT, padx=(10, 0))

    def _setup_callbacks(self) -> None:
        """Setup serial and WiFi manager callbacks."""
        # Serial (main winch)
        self._serial_manager.set_status_callback(self._on_status_update)
        self._serial_manager.set_connection_callback(self._on_connection_change)
        self._serial_manager.set_command_sent_callback(self._on_command_sent)
        self._serial_manager.set_response_callback(self._on_response_received)
        self._serial_manager.set_error_callback(self._on_error)

        # Drop cylinder (WiFi or Serial)
        self._drop_cylinder_manager.set_status_callback(self._on_drop_status_update)
        self._drop_cylinder_manager.set_connection_callback(self._on_drop_connection_change)
        self._drop_cylinder_manager.set_error_callback(self._on_drop_error)

    def _setup_keyboard_bindings(self) -> None:
        """Setup keyboard shortcuts."""
        # Jog controls (press and release)
        self._root.bind("<KeyPress-Left>", self._on_key_left_press)
        self._root.bind("<KeyRelease-Left>", self._on_key_left_release)
        self._root.bind("<KeyPress-Right>", self._on_key_right_press)
        self._root.bind("<KeyRelease-Right>", self._on_key_right_release)

        # Stop controls
        self._root.bind("<space>", self._on_key_stop)
        self._root.bind("<Escape>", self._on_key_stop)

        # Quick actions
        self._root.bind("<h>", self._on_key_home)
        self._root.bind("<H>", self._on_key_home)
        self._root.bind("<w>", self._on_key_well)
        self._root.bind("<W>", self._on_key_well)

        # Focus handling - prevent keys from triggering in entry fields
        self._root.bind_class("TEntry", "<KeyPress>", lambda e: "break" if e.keysym in ("Left", "Right", "space", "Escape") else None, add=True)

    def _refresh_ports(self) -> None:
        """Refresh the list of available serial ports."""
        ports = SerialManager.list_ports()
        self._port_combo["values"] = ports

        if ports:
            # Try to keep current selection or select first port
            current = self._port_var.get()
            if current not in ports:
                self._port_var.set(ports[0])
        else:
            self._port_var.set("")

    def _toggle_connection(self) -> None:
        """Connect or disconnect from serial port."""
        if self._serial_manager.is_connected:
            self._serial_manager.disconnect()
        else:
            port = self._port_var.get()
            if not port:
                messagebox.showwarning("No Port", "Please select a serial port.")
                return

            try:
                baud = int(self._baud_var.get())
            except ValueError:
                baud = self.DEFAULT_BAUD

            self._serial_manager.connect(port, baud)

    def _update_controls_state(self) -> None:
        """Update control states based on connection and E-stop."""
        connected = self._serial_manager.is_connected
        status = self._serial_manager.last_status
        estop = status.estop_active if status else False

        # Enable/disable controls
        enabled = connected and not estop
        self._control_panel.set_enabled(enabled)
        self._settings_panel.set_enabled(enabled)

        # Update home/well button states
        if status:
            self._control_panel.set_home_enabled(enabled and status.home_saved)
            self._control_panel.set_well_enabled(enabled and status.well_saved)
        else:
            self._control_panel.set_home_enabled(False)
            self._control_panel.set_well_enabled(False)

        # Update connection button text
        self._connect_btn.configure(
            text="Disconnect" if connected else "Connect"
        )

        # Disable port selection when connected
        port_state = "disabled" if connected else "readonly"
        self._port_combo.configure(state=port_state)
        self._baud_combo.configure(state=port_state)

    # Serial callbacks (called from background thread)

    def _on_status_update(self, status: WinchStatus) -> None:
        """Handle status update from serial manager."""
        # Schedule GUI update on main thread
        self._root.after(0, self._update_status_display, status)

    def _on_connection_change(self, state: ConnectionState, message: str) -> None:
        """Handle connection state change."""
        self._root.after(0, self._update_connection_display, state, message)

    def _on_command_sent(self, command: str) -> None:
        """Handle command sent notification."""
        self._root.after(0, self._status_bar.set_last_command, command)

    def _on_response_received(self, response: str) -> None:
        """Handle response received notification."""
        self._root.after(0, self._status_bar.set_last_response, response)

    def _on_error(self, message: str) -> None:
        """Handle error notification."""
        self._root.after(0, self._show_error, message)

    # GUI update methods (called on main thread)

    def _update_status_display(self, status: WinchStatus) -> None:
        """Update all displays with new status."""
        self._position_display.update_status(status)
        self._settings_panel.update_home_position(status.home_saved, status.home_position)
        self._settings_panel.update_well_position(status.well_saved, status.well_position)
        self._status_bar.set_estop_active(status.estop_active)
        self._status_bar.set_last_comm_time(self._serial_manager.last_response_time)
        self._update_controls_state()

    def _update_connection_display(self, state: ConnectionState, message: str) -> None:
        """Update connection status display."""
        self._status_bar.set_connection_state(state, message)
        self._update_controls_state()

        if state == ConnectionState.DISCONNECTED:
            self._position_display.set_disconnected()
            self._status_bar.set_estop_active(False)

    def _show_error(self, message: str) -> None:
        """Show error message to user."""
        messagebox.showerror("Error", message)

    # Control callbacks

    def _on_jog_left_press(self) -> None:
        """Handle jog left press."""
        self._serial_manager.jog_left()

    def _on_jog_left_release(self) -> None:
        """Handle jog left release."""
        self._serial_manager.jog_stop()

    def _on_jog_right_press(self) -> None:
        """Handle jog right press."""
        self._serial_manager.jog_right()

    def _on_jog_right_release(self) -> None:
        """Handle jog right release."""
        self._serial_manager.jog_stop()

    def _on_go_home(self) -> None:
        """Handle go home button."""
        self._serial_manager.go_home()

    def _on_go_well(self) -> None:
        """Handle go well button."""
        self._serial_manager.go_well()

    def _on_stop(self) -> None:
        """Handle stop button."""
        self._serial_manager.stop()

    def _on_go_to(self, steps: int) -> None:
        """Handle go to absolute position."""
        self._serial_manager.go_to_position(steps)

    def _on_move_relative(self, steps: int) -> None:
        """Handle relative move."""
        self._serial_manager.move_relative(steps)

    def _on_save_home(self) -> None:
        """Handle save home button."""
        self._serial_manager.save_home()

    def _on_save_well(self) -> None:
        """Handle save well button."""
        self._serial_manager.save_well()

    def _on_zero_position(self) -> None:
        """Handle zero position button (go to 0)."""
        self._serial_manager.go_to_position(0)

    def _open_settings(self) -> None:
        """Open speed settings dialog."""
        status = self._serial_manager.last_status
        jog_rps = status.max_jog_rps if status else 10.0
        move_rps = status.max_move_rps if status else 7.5

        SettingsDialog(
            self._root,
            current_jog_rps=jog_rps,
            current_move_rps=move_rps,
            on_apply=self._apply_speed_settings
        )

    def _apply_speed_settings(self, jog_rps: float, move_rps: float) -> None:
        """Apply new speed settings."""
        if self._serial_manager.is_connected:
            self._serial_manager.set_jog_speed(jog_rps)
            self._serial_manager.set_move_speed(move_rps)

    # Drop cylinder callbacks

    def _on_drop_connect_wifi(self, ip: str, port: int) -> None:
        """Connect to drop cylinder ESP32 via WiFi."""
        self._drop_error_shown = False
        self._drop_cylinder_manager.connect_wifi(ip, port)

    def _on_drop_connect_serial(self, port: str, baudrate: int) -> None:
        """Connect to drop cylinder ESP32 via serial."""
        self._drop_error_shown = False
        self._drop_cylinder_manager.connect_serial(port, baudrate)

    def _on_drop_disconnect(self) -> None:
        """Disconnect from drop cylinder."""
        self._drop_cylinder_manager.disconnect()

    def _on_drop_refresh_ports(self) -> list:
        """Refresh and return available serial ports for drop cylinder."""
        return DropCylinderManager.list_serial_ports()

    def _on_drop_status_update(self, status: DropCylinderStatus) -> None:
        """Handle drop cylinder status update."""
        self._root.after(0, self._drop_cylinder_panel.update_status, status)

    def _on_drop_connection_change(self, state: DropCylinderConnectionState, message: str) -> None:
        """Handle drop cylinder connection state change."""
        connected = (state == DropCylinderConnectionState.CONNECTED)
        mode = self._drop_cylinder_manager.mode
        self._root.after(0, self._drop_cylinder_panel.set_connection_state, state, connected, mode)
        self._root.after(0, self._drop_cylinder_panel.set_enabled, connected)
        if not connected:
            self._root.after(0, self._drop_cylinder_panel.update_status, None)
            # Show message if connection was lost unexpectedly
            if "Connection lost" in message:
                if mode == ConnectionMode.SERIAL:
                    warn_msg = "Connection to the drop cylinder has been lost.\nPlease check the USB connection."
                else:
                    warn_msg = "Connection to the drop cylinder has been lost.\nPlease check your WiFi connection."
                self._root.after(0, lambda m=warn_msg: messagebox.showwarning(
                    "Drop Cylinder Disconnected", m
                ))

    def _on_drop_error(self, message: str) -> None:
        """Handle drop cylinder error (only show once per connection attempt)."""
        if not self._drop_error_shown:
            self._drop_error_shown = True
            self._root.after(0, lambda: messagebox.showerror("Drop Cylinder Error", message))

    def _on_drop_jog_down_press(self) -> None:
        self._drop_cylinder_manager.jog_down()

    def _on_drop_jog_down_release(self) -> None:
        self._drop_cylinder_manager.jog_stop()

    def _on_drop_jog_up_press(self) -> None:
        self._drop_cylinder_manager.jog_up()

    def _on_drop_jog_up_release(self) -> None:
        self._drop_cylinder_manager.jog_stop()

    def _on_drop_go_start(self) -> None:
        self._drop_cylinder_manager.go_start()

    def _on_drop_go_stop(self) -> None:
        self._drop_cylinder_manager.go_stop_position()

    def _on_drop_save_start(self) -> None:
        self._drop_cylinder_manager.save_start()

    def _on_drop_save_stop(self) -> None:
        self._drop_cylinder_manager.save_stop()

    def _on_drop_stop(self) -> None:
        self._drop_cylinder_manager.stop()

    def _on_drop_set_trim(self, offset_us: int) -> None:
        self._drop_cylinder_manager.set_trim(offset_us)

    def _on_drop_set_speed(self, percent: int) -> None:
        self._drop_cylinder_manager.set_speed(percent)

    def _on_drop_configure_wifi(self, ssid: str, password: str) -> None:
        if self._drop_cylinder_manager.is_connected:
            self._drop_cylinder_manager.set_wifi_credentials(ssid, password)
        else:
            messagebox.showwarning("Not Connected", "Connect to the ESP32 first (in AP mode) to configure WiFi.")

    def _on_drop_test(self) -> None:
        self._drop_cylinder_manager.send_command("TEST")

    # Keyboard handlers

    def _on_key_left_press(self, event: tk.Event) -> None:
        """Handle left arrow key press."""
        if not self._serial_manager.is_connected:
            return
        # Check if focus is in an entry widget
        if isinstance(self._root.focus_get(), ttk.Entry):
            return
        if "Left" not in self._pressed_keys:
            self._pressed_keys.add("Left")
            self._control_panel.trigger_jog_left(True)

    def _on_key_left_release(self, event: tk.Event) -> None:
        """Handle left arrow key release."""
        if "Left" in self._pressed_keys:
            self._pressed_keys.discard("Left")
            self._control_panel.trigger_jog_left(False)

    def _on_key_right_press(self, event: tk.Event) -> None:
        """Handle right arrow key press."""
        if not self._serial_manager.is_connected:
            return
        # Check if focus is in an entry widget
        if isinstance(self._root.focus_get(), ttk.Entry):
            return
        if "Right" not in self._pressed_keys:
            self._pressed_keys.add("Right")
            self._control_panel.trigger_jog_right(True)

    def _on_key_right_release(self, event: tk.Event) -> None:
        """Handle right arrow key release."""
        if "Right" in self._pressed_keys:
            self._pressed_keys.discard("Right")
            self._control_panel.trigger_jog_right(False)

    def _on_key_stop(self, event: tk.Event) -> None:
        """Handle stop key (space/escape)."""
        if not self._serial_manager.is_connected:
            return
        # Check if focus is in an entry widget (allow space in entries)
        if isinstance(self._root.focus_get(), ttk.Entry) and event.keysym == "space":
            return
        self._on_stop()

    def _on_key_home(self, event: tk.Event) -> None:
        """Handle home key (H)."""
        if not self._serial_manager.is_connected:
            return
        if isinstance(self._root.focus_get(), ttk.Entry):
            return
        status = self._serial_manager.last_status
        if status and status.home_saved:
            self._on_go_home()

    def _on_key_well(self, event: tk.Event) -> None:
        """Handle well key (W)."""
        if not self._serial_manager.is_connected:
            return
        if isinstance(self._root.focus_get(), ttk.Entry):
            return
        status = self._serial_manager.last_status
        if status and status.well_saved:
            self._on_go_well()

    def _on_close(self) -> None:
        """Handle window close."""
        # Disconnect if connected
        if self._serial_manager.is_connected:
            self._serial_manager.disconnect()
        if self._drop_cylinder_manager.is_connected:
            self._drop_cylinder_manager.disconnect()

        self._root.destroy()

    def run(self) -> None:
        """Start the main event loop."""
        self._root.mainloop()
