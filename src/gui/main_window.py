"""
Main Application Window

Integrates all GUI components and handles keyboard shortcuts.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Set

from ..config import (
    SERIAL_BAUD_RATES,
    SERIAL_BAUD_DEFAULT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_TITLE,
    DEFAULT_JOG_SPEED_RPS,
    DEFAULT_MOVE_SPEED_RPS,
    STAC5_HOST,
    STAC5_TCP_PORT,
    STAC5_POLL_INTERVAL_SEC,
    STEPS_PER_REVOLUTION,
)
from ..serial_manager import SerialManager, ConnectionState
from ..wifi_manager import DropCylinderManager, DropCylinderConnectionState, ConnectionMode
from ..drop_cylinder_protocol import DropCylinderStatus
from ..command_protocol import WinchStatus, MotionMode
from ..stac5_manager import STAC5Manager, STAC5Status
from .position_display import PositionDisplay, PositionSlider
from .control_panel import ControlPanel
from .settings_panel import SettingsPanel
from .status_bar import StatusBar
from .settings_dialog import SettingsDialog
from .drop_cylinder_panel import DropCylinderPanel
from .camera_panel import CameraPanel
from .theme import COLORS, FONTS
from .widgets import ModernButton

# Backward compatibility aliases
WifiManager = DropCylinderManager
WifiConnectionState = DropCylinderConnectionState


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

    WINDOW_TITLE_CONST = WINDOW_TITLE
    WINDOW_MIN_WIDTH_CONST = WINDOW_MIN_WIDTH
    WINDOW_MIN_HEIGHT_CONST = WINDOW_MIN_HEIGHT

    # Default baud rates
    BAUD_RATES = SERIAL_BAUD_RATES
    DEFAULT_BAUD = SERIAL_BAUD_DEFAULT

    def __init__(self, root: tk.Tk):
        self._root = root
        self._serial_manager = SerialManager()
        self._drop_cylinder_manager = DropCylinderManager()
        self._stac5_manager = STAC5Manager(STAC5_HOST, STAC5_TCP_PORT)

        # Track pressed keys for jog
        self._pressed_keys: Set[str] = set()

        # Track if we've shown a drop cylinder error (to avoid spam)
        self._drop_error_shown = False

        # Track STAC5 connection errors
        self._stac5_error_shown = False

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
        self._root.title(self.WINDOW_TITLE_CONST)
        self._root.minsize(self.WINDOW_MIN_WIDTH_CONST, self.WINDOW_MIN_HEIGHT_CONST)
        self._root.columnconfigure(0, weight=1)

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Configure grid for two-column layout
        self._root.columnconfigure(0, weight=0)  # Left column (controls) - fixed
        self._root.columnconfigure(1, weight=1)  # Right column (cameras) - expandable
        self._root.rowconfigure(6, weight=1)     # Let the camera row expand

        # Connection Bar (spans all columns)
        self._create_connection_bar()

        # Separator (spans both columns)
        ttk.Separator(self._root, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=2
        )

        # === POSITION SLIDER (spans both columns) ===
        self._position_slider = PositionSlider(self._root, height=70)
        self._position_slider.grid(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=0)

        # === LEFT COLUMN (Controls) ===

        # Position Display
        self._position_display = PositionDisplay(self._root)
        self._position_display.grid(row=3, column=0, sticky="ew", padx=5, pady=2)

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
        self._control_panel.grid(row=4, column=0, sticky="ew", padx=5, pady=2)

        # Settings Panel
        self._settings_panel = SettingsPanel(
            self._root,
            on_save_home=self._on_save_home,
            on_save_well=self._on_save_well,
            on_zero_position=self._on_zero_position,
            on_clear_fault=self._on_clear_fault
        )
        self._settings_panel.grid(row=5, column=0, sticky="ew", padx=5, pady=2)

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
        self._drop_cylinder_panel.grid(row=6, column=0, sticky="new", padx=5, pady=2)

        # === RIGHT COLUMN (Cameras in container) ===

        # Container frame for cameras (anchored top-left, no stretching)
        camera_container = tk.Frame(self._root, bg=COLORS['bg_dark'])
        camera_container.grid(row=3, column=1, rowspan=4, sticky="nw", padx=5, pady=2)

        # Camera Panel 1 (fixed size, no expand)
        self._camera_panel = CameraPanel(camera_container)
        self._camera_panel.pack(side='left', padx=(0, 2))

        # Camera Panel 2 (fixed size, no expand)
        self._camera_panel_2 = CameraPanel(camera_container)
        self._camera_panel_2.pack(side='left', padx=(2, 0))

        # === BOTTOM ROW (Status Bar spans both columns) ===

        # Status Bar
        self._status_bar = StatusBar(self._root)
        self._status_bar.grid(row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=2)

    def _create_connection_bar(self) -> None:
        """Create the connection controls bar with STAC5 and legacy serial options."""
        # Outer container with border (spans both columns)
        conn_outer = tk.Frame(self._root, bg=COLORS['border'], padx=1, pady=1)
        conn_outer.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

        conn_frame = tk.Frame(conn_outer, bg=COLORS['bg_header'], padx=12, pady=8)
        conn_frame.pack(fill='x')

        # === STAC5 Motor Controller Connection (Primary) ===
        stac5_label = tk.Label(conn_frame, text="STAC5:", font=FONTS['subheading'],
                               bg=COLORS['bg_header'], fg=COLORS['text_primary'])
        stac5_label.pack(side=tk.LEFT, padx=(0, 6))

        # IP Address entry
        self._stac5_ip_var = tk.StringVar(value=STAC5_HOST)
        self._stac5_ip_entry = ttk.Entry(conn_frame, textvariable=self._stac5_ip_var, width=14)
        self._stac5_ip_entry.pack(side=tk.LEFT, padx=(0, 6))

        # Port entry
        port_label = tk.Label(conn_frame, text=":", font=FONTS['body'],
                              bg=COLORS['bg_header'], fg=COLORS['text_secondary'])
        port_label.pack(side=tk.LEFT)

        self._stac5_port_var = tk.StringVar(value=str(STAC5_TCP_PORT))
        self._stac5_port_entry = ttk.Entry(conn_frame, textvariable=self._stac5_port_var, width=5)
        self._stac5_port_entry.pack(side=tk.LEFT, padx=(0, 8))

        # STAC5 Connect/Disconnect button
        self._stac5_connect_btn = ModernButton(
            conn_frame,
            text="Connect",
            command=self._toggle_stac5_connection,
            width=100,
            height=32,
            bg_color=COLORS['btn_primary'],
            glow=True,
            font=FONTS['button']
        )
        self._stac5_connect_btn.pack(side=tk.LEFT)

        # STAC5 status indicator
        self._stac5_status_label = tk.Label(
            conn_frame, text="\u25CF", font=FONTS['body'],
            bg=COLORS['bg_header'], fg=COLORS['text_secondary']
        )
        self._stac5_status_label.pack(side=tk.LEFT, padx=(8, 0))

        # Separator
        sep = tk.Frame(conn_frame, width=2, height=28, bg=COLORS['border'])
        sep.pack(side=tk.LEFT, padx=16)

        # === Legacy Serial Connection (for other devices) ===
        legacy_label = tk.Label(conn_frame, text="Serial:", font=FONTS['body'],
                                bg=COLORS['bg_header'], fg=COLORS['text_secondary'])
        legacy_label.pack(side=tk.LEFT, padx=(0, 6))

        self._port_var = tk.StringVar()
        self._port_combo = ttk.Combobox(
            conn_frame,
            textvariable=self._port_var,
            width=10,
            state="readonly"
        )
        self._port_combo.pack(side=tk.LEFT, padx=(0, 4))

        # Refresh ports button
        self._refresh_btn = ModernButton(
            conn_frame,
            text="\u21BB",
            command=self._refresh_ports,
            width=28,
            height=28,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['body']
        )
        self._refresh_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Baud rate selection
        self._baud_var = tk.StringVar(value=str(self.DEFAULT_BAUD))
        self._baud_combo = ttk.Combobox(
            conn_frame,
            textvariable=self._baud_var,
            values=[str(b) for b in self.BAUD_RATES],
            width=7,
            state="readonly"
        )
        self._baud_combo.pack(side=tk.LEFT, padx=(0, 8))

        # Serial Connect/Disconnect button
        self._connect_btn = ModernButton(
            conn_frame,
            text="Connect",
            command=self._toggle_connection,
            width=80,
            height=28,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['body']
        )
        self._connect_btn.pack(side=tk.LEFT)

        # Settings button
        self._settings_btn = ModernButton(
            conn_frame,
            text="\u2699",
            command=self._open_settings,
            width=36,
            height=32,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['button']
        )
        self._settings_btn.pack(side=tk.LEFT, padx=(16, 0))

    def _setup_callbacks(self) -> None:
        """Setup serial, WiFi, and STAC5 manager callbacks."""
        # Serial (legacy winch - kept for reference)
        self._serial_manager.set_status_callback(self._on_status_update)
        self._serial_manager.set_connection_callback(self._on_connection_change)
        self._serial_manager.set_command_sent_callback(self._on_command_sent)
        self._serial_manager.set_response_callback(self._on_response_received)
        self._serial_manager.set_error_callback(self._on_error)

        # STAC5 Motor Controller (primary)
        self._stac5_manager.set_status_callback(self._on_stac5_status_update)
        self._stac5_manager.set_error_callback(self._on_stac5_error)

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
        """Update control states based on STAC5 connection status."""
        # Check STAC5 connection (primary control)
        stac5_connected = self._stac5_manager.is_connected()
        stac5_status = self._stac5_manager.status

        # Check legacy serial connection
        serial_connected = self._serial_manager.is_connected
        serial_status = self._serial_manager.last_status
        estop = serial_status.estop_active if serial_status else False

        # Enable controls if STAC5 is connected (primary) or serial is connected (legacy)
        enabled = stac5_connected or (serial_connected and not estop)
        self._control_panel.set_enabled(enabled)
        self._settings_panel.set_enabled(enabled)

        # Update home/well button states based on STAC5 or serial status
        if stac5_connected:
            self._control_panel.set_home_enabled(enabled and stac5_status.home_position is not None)
            self._control_panel.set_well_enabled(enabled and stac5_status.well_position is not None)
        elif serial_status:
            self._control_panel.set_home_enabled(enabled and serial_status.home_saved)
            self._control_panel.set_well_enabled(enabled and serial_status.well_saved)
        else:
            self._control_panel.set_home_enabled(False)
            self._control_panel.set_well_enabled(False)

        # Update STAC5 connection button text and color
        if stac5_connected:
            self._stac5_connect_btn.set_text("Disconnect")
            self._stac5_connect_btn.configure_colors(bg_color=COLORS['btn_danger'])
            self._stac5_status_label.configure(fg=COLORS['accent_green'])
            self._stac5_ip_entry.configure(state="disabled")
            self._stac5_port_entry.configure(state="disabled")
        else:
            self._stac5_connect_btn.set_text("Connect")
            self._stac5_connect_btn.configure_colors(bg_color=COLORS['btn_primary'])
            self._stac5_status_label.configure(fg=COLORS['text_secondary'])
            self._stac5_ip_entry.configure(state="normal")
            self._stac5_port_entry.configure(state="normal")

        # Update legacy serial connection button text and color
        if serial_connected:
            self._connect_btn.set_text("Disconnect")
            self._connect_btn.configure_colors(bg_color=COLORS['btn_danger'])
        else:
            self._connect_btn.set_text("Connect")
            self._connect_btn.configure_colors(bg_color=COLORS['btn_secondary'])

        # Disable port selection when connected
        port_state = "disabled" if serial_connected else "readonly"
        self._port_combo.configure(state=port_state)
        self._baud_combo.configure(state=port_state)

    # =========================================================================
    # STAC5 Motor Controller Methods
    # =========================================================================

    def _toggle_stac5_connection(self) -> None:
        """Connect or disconnect from STAC5 motor controller."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.disconnect()
            self._update_controls_state()
            self._status_bar.set_connection_state(ConnectionState.DISCONNECTED, "STAC5 Disconnected")
            self._position_display.set_disconnected()
            self._position_slider.set_disconnected()
        else:
            ip = self._stac5_ip_var.get().strip()
            try:
                port = int(self._stac5_port_var.get())
            except ValueError:
                port = STAC5_TCP_PORT

            # Update manager with new IP/port
            self._stac5_manager.host = ip
            self._stac5_manager.port = port

            self._status_bar.set_connection_state(ConnectionState.CONNECTING, f"Connecting to {ip}:{port}...")

            # Connect in background to avoid blocking GUI
            import threading
            def connect_thread():
                success = self._stac5_manager.connect()
                if success:
                    self._stac5_manager.start_polling(STAC5_POLL_INTERVAL_SEC)
                self._root.after(0, self._on_stac5_connect_result, success)

            threading.Thread(target=connect_thread, daemon=True).start()

    def _on_stac5_connect_result(self, success: bool) -> None:
        """Handle STAC5 connection result (called on main thread)."""
        if success:
            self._status_bar.set_connection_state(
                ConnectionState.CONNECTED,
                f"Connected to STAC5 at {self._stac5_manager.host}"
            )
            self._stac5_error_shown = False
        else:
            self._status_bar.set_connection_state(
                ConnectionState.DISCONNECTED,
                "STAC5 connection failed"
            )
            if not self._stac5_error_shown:
                self._stac5_error_shown = True
                messagebox.showerror(
                    "Connection Failed",
                    f"Could not connect to STAC5 at {self._stac5_manager.host}:{self._stac5_manager.port}\n\n"
                    "Please check:\n"
                    "- The STAC5 is powered on\n"
                    "- The IP address is correct\n"
                    "- Network connectivity (Starlink)"
                )
        self._update_controls_state()

    def _on_stac5_status_update(self, status: STAC5Status) -> None:
        """Handle STAC5 status update (called from background thread)."""
        self._root.after(0, self._update_stac5_status_display, status)

    def _update_stac5_status_display(self, status: STAC5Status) -> None:
        """Update displays with STAC5 status (called on main thread)."""
        # Create a WinchStatus-compatible object for the position display
        # This allows reusing the existing position display widget
        class STAC5WinchStatus:
            def __init__(self, s: STAC5Status):
                self.position = s.encoder_position
                self.is_moving = s.is_moving
                self.motor_enabled = s.motor_enabled
                self.estop_active = False
                self.home_saved = s.home_position is not None
                self.well_saved = s.well_position is not None
                self.home_position = s.home_position if s.home_position else 0
                self.well_position = s.well_position if s.well_position else 0
                self.max_jog_rps = s.jog_velocity
                self.max_move_rps = s.move_velocity
                # Motion mode based on is_moving flag
                self.mode = MotionMode.JOG if s.is_moving else MotionMode.IDLE
                # Speed - we don't have real-time velocity from STAC5, show jog velocity
                self.speed_rps = s.jog_velocity if s.is_moving else 0.0

            @property
            def position_revolutions(self) -> float:
                return self.position / STEPS_PER_REVOLUTION

        compat_status = STAC5WinchStatus(status)
        self._position_display.update_status(compat_status)
        self._settings_panel.update_home_position(status.home_position is not None, status.home_position or 0)
        self._settings_panel.update_well_position(status.well_position is not None, status.well_position or 0)

        # Update position slider
        self._position_slider.update_position(
            status.encoder_position,
            status.home_position,
            status.well_position
        )

        self._update_controls_state()

    def _on_stac5_error(self, message: str) -> None:
        """Handle STAC5 error (called from background thread)."""
        self._root.after(0, self._show_stac5_error, message)

    def _show_stac5_error(self, message: str) -> None:
        """Show STAC5 error message (called on main thread)."""
        self._status_bar.set_connection_state(ConnectionState.ERROR, f"STAC5: {message}")
        # Don't spam error dialogs
        if not self._stac5_error_shown:
            self._stac5_error_shown = True
            messagebox.showerror("STAC5 Error", message)

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
            self._position_slider.set_disconnected()
            self._status_bar.set_estop_active(False)

    def _show_error(self, message: str) -> None:
        """Show error message to user."""
        messagebox.showerror("Error", message)

    # Control callbacks (routes to STAC5 if connected, otherwise serial)

    def _on_jog_left_press(self) -> None:
        """Handle jog left press."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.jog_start(-1)  # Negative direction
        else:
            self._serial_manager.jog_left()

    def _on_jog_left_release(self) -> None:
        """Handle jog left release."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.jog_stop()
        else:
            self._serial_manager.jog_stop()

    def _on_jog_right_press(self) -> None:
        """Handle jog right press."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.jog_start(1)  # Positive direction
        else:
            self._serial_manager.jog_right()

    def _on_jog_right_release(self) -> None:
        """Handle jog right release."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.jog_stop()
        else:
            self._serial_manager.jog_stop()

    def _on_go_home(self) -> None:
        """Handle go home button."""
        if self._stac5_manager.is_connected():
            # Run in background to avoid blocking polling/GUI updates
            import threading
            threading.Thread(target=self._stac5_manager.go_home, daemon=True).start()
        else:
            self._serial_manager.go_home()

    def _on_go_well(self) -> None:
        """Handle go well button."""
        if self._stac5_manager.is_connected():
            # Run in background to avoid blocking polling/GUI updates
            import threading
            threading.Thread(target=self._stac5_manager.go_well, daemon=True).start()
        else:
            self._serial_manager.go_well()

    def _on_stop(self) -> None:
        """Handle stop button."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.stop()
        else:
            self._serial_manager.stop()

    def _on_go_to(self, steps: int) -> None:
        """Handle go to absolute position."""
        if self._stac5_manager.is_connected():
            # Run in background to avoid blocking polling/GUI updates
            import threading
            threading.Thread(target=self._stac5_manager.move_to_position, args=(steps,), daemon=True).start()
        else:
            self._serial_manager.go_to_position(steps)

    def _on_move_relative(self, steps: int) -> None:
        """Handle relative move."""
        if self._stac5_manager.is_connected():
            # Run in background to avoid blocking polling/GUI updates
            import threading
            threading.Thread(target=self._stac5_manager.move_relative, args=(steps,), daemon=True).start()
        else:
            self._serial_manager.move_relative(steps)

    def _on_save_home(self) -> None:
        """Handle save home button."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.save_home()
        else:
            self._serial_manager.save_home()

    def _on_save_well(self) -> None:
        """Handle save well button."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.save_well()
        else:
            self._serial_manager.save_well()

    def _on_zero_position(self) -> None:
        """Handle zero position button (set current position as 0)."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.zero_encoder()
        else:
            self._serial_manager.zero_position()

    def _on_clear_fault(self) -> None:
        """Handle clear fault button."""
        if self._stac5_manager.is_connected():
            old_alarm = self._stac5_manager.status.alarm_code
            self._stac5_manager.alarm_reset()
            # Also re-enable motor after clearing fault
            self._stac5_manager.motor_enable()
            print(f"[STAC5] Fault cleared (was: {old_alarm})")
            self._status_bar.set_last_response(f"Fault {old_alarm} cleared")

    def _open_settings(self) -> None:
        """Open speed settings dialog."""
        # Get current settings from STAC5 or serial manager
        if self._stac5_manager.is_connected():
            jog_rps = self._stac5_manager.status.jog_velocity
            move_rps = self._stac5_manager.status.move_velocity
        else:
            status = self._serial_manager.last_status
            jog_rps = status.max_jog_rps if status else DEFAULT_JOG_SPEED_RPS
            move_rps = status.max_move_rps if status else DEFAULT_MOVE_SPEED_RPS

        SettingsDialog(
            self._root,
            current_jog_rps=jog_rps,
            current_move_rps=move_rps,
            on_apply=self._apply_speed_settings
        )

    def _apply_speed_settings(self, jog_rps: float, move_rps: float) -> None:
        """Apply new speed settings."""
        if self._stac5_manager.is_connected():
            self._stac5_manager.set_jog_velocity(jog_rps)
            self._stac5_manager.set_move_velocity(move_rps)
        elif self._serial_manager.is_connected:
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

    def _is_motor_connected(self) -> bool:
        """Check if any motor controller is connected (STAC5 or serial)."""
        return self._stac5_manager.is_connected() or self._serial_manager.is_connected

    def _on_key_left_press(self, event: tk.Event) -> None:
        """Handle left arrow key press."""
        if not self._is_motor_connected():
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
        if not self._is_motor_connected():
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
        if not self._is_motor_connected():
            return
        # Check if focus is in an entry widget (allow space in entries)
        if isinstance(self._root.focus_get(), ttk.Entry) and event.keysym == "space":
            return
        self._on_stop()

    def _on_key_home(self, event: tk.Event) -> None:
        """Handle home key (H)."""
        if not self._is_motor_connected():
            return
        if isinstance(self._root.focus_get(), ttk.Entry):
            return
        # Check STAC5 first, then serial
        if self._stac5_manager.is_connected():
            if self._stac5_manager.status.home_position is not None:
                self._on_go_home()
        else:
            status = self._serial_manager.last_status
            if status and status.home_saved:
                self._on_go_home()

    def _on_key_well(self, event: tk.Event) -> None:
        """Handle well key (W)."""
        if not self._is_motor_connected():
            return
        if isinstance(self._root.focus_get(), ttk.Entry):
            return
        # Check STAC5 first, then serial
        if self._stac5_manager.is_connected():
            if self._stac5_manager.status.well_position is not None:
                self._on_go_well()
        else:
            status = self._serial_manager.last_status
            if status and status.well_saved:
                self._on_go_well()

    def _on_close(self) -> None:
        """Handle window close."""
        # Disconnect if connected
        if self._stac5_manager.is_connected():
            self._stac5_manager.disconnect()
        if self._serial_manager.is_connected:
            self._serial_manager.disconnect()
        if self._drop_cylinder_manager.is_connected:
            self._drop_cylinder_manager.disconnect()

        self._root.destroy()

    def run(self) -> None:
        """Start the main event loop."""
        self._root.mainloop()
