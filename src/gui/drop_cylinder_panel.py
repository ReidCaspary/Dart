"""
Drop Cylinder Control Panel

Controls for the ESP32-based servo winch drop cylinder system.
Supports both WiFi and USB serial connections.
Modern dark theme styling.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List

from ..wifi_manager import WifiConnectionState, ConnectionMode
from ..drop_cylinder_protocol import DropCylinderStatus
from .theme import COLORS, FONTS
from .widgets import ModernButton, HoldButton, LEDIndicator, ModernEntry, ModernScale


class DropCylinderPanel(tk.Frame):
    """
    Control panel for the drop cylinder servo winch.
    Supports both WiFi/TCP and USB serial connections.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_connect_wifi: Callable[[str, int], None],
        on_connect_serial: Callable[[str, int], None],
        on_disconnect: Callable[[], None],
        on_refresh_ports: Callable[[], List[str]],
        on_jog_down_press: Callable[[], None],
        on_jog_down_release: Callable[[], None],
        on_jog_up_press: Callable[[], None],
        on_jog_up_release: Callable[[], None],
        on_go_start: Callable[[], None],
        on_go_stop: Callable[[], None],
        on_save_start: Callable[[], None],
        on_save_stop: Callable[[], None],
        on_stop: Callable[[], None],
        on_set_trim: Callable[[int], None],
        on_set_speed: Callable[[int], None],
        on_configure_wifi: Callable[[str, str], None],
        on_test: Callable[[], None] = None
    ):
        super().__init__(parent, bg=COLORS['bg_dark'])

        # Store callbacks
        self._on_connect_wifi = on_connect_wifi
        self._on_connect_serial = on_connect_serial
        self._on_disconnect = on_disconnect
        self._on_refresh_ports = on_refresh_ports
        self._on_jog_down_press = on_jog_down_press
        self._on_jog_down_release = on_jog_down_release
        self._on_jog_up_press = on_jog_up_press
        self._on_jog_up_release = on_jog_up_release
        self._on_go_start = on_go_start
        self._on_go_stop = on_go_stop
        self._on_save_start = on_save_start
        self._on_save_stop = on_save_stop
        self._on_stop = on_stop
        self._on_set_trim = on_set_trim
        self._on_set_speed = on_set_speed
        self._on_configure_wifi = on_configure_wifi
        self._on_test = on_test

        self._connected = False
        self._connection_mode: Optional[ConnectionMode] = None
        self._jog_down_active = False
        self._jog_up_active = False

        # Track trim state for auto-disable on stop
        self._saved_trim_value = 0
        self._trim_zeroed = False

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create panel widgets."""
        self.columnconfigure(0, weight=1)

        # Main panel border
        panel_border = tk.Frame(self, bg=COLORS['border'])
        panel_border.grid(row=0, column=0, sticky="ew", padx=8, pady=4)

        panel_frame = tk.Frame(panel_border, bg=COLORS['bg_panel'], padx=12, pady=10)
        panel_frame.pack(fill='both', padx=1, pady=1)

        # Header
        header = tk.Label(
            panel_frame,
            text="DROP CYLINDER",
            font=FONTS['heading'],
            fg=COLORS['text_accent'],
            bg=COLORS['bg_panel']
        )
        header.pack(anchor='w')

        # === Mode Selection Row ===
        mode_frame = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        mode_frame.pack(fill='x', pady=(8, 0))

        mode_label = tk.Label(
            mode_frame,
            text="Mode:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        mode_label.pack(side='left')

        self._conn_mode_var = tk.StringVar(value="wifi")
        self._wifi_radio = ttk.Radiobutton(
            mode_frame, text="WiFi", variable=self._conn_mode_var,
            value="wifi", command=self._on_mode_change
        )
        self._wifi_radio.pack(side='left', padx=(8, 4))

        self._serial_radio = ttk.Radiobutton(
            mode_frame, text="Serial", variable=self._conn_mode_var,
            value="serial", command=self._on_mode_change
        )
        self._serial_radio.pack(side='left', padx=4)

        # === Connection Row ===
        conn_frame = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        conn_frame.pack(fill='x', pady=(8, 0))

        # WiFi widgets
        self._wifi_frame = tk.Frame(conn_frame, bg=COLORS['bg_panel'])
        self._wifi_frame.pack(side='left')

        ip_label = tk.Label(
            self._wifi_frame,
            text="IP:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        ip_label.pack(side='left')

        self._ip_var = tk.StringVar(value="192.168.1.10")
        self._ip_entry = ModernEntry(self._wifi_frame, width=14)
        self._ip_entry.insert(0, "192.168.1.10")
        self._ip_entry.pack(side='left', padx=(4, 0))

        # Serial widgets (hidden initially)
        self._serial_frame = tk.Frame(conn_frame, bg=COLORS['bg_panel'])

        port_label = tk.Label(
            self._serial_frame,
            text="Port:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        port_label.pack(side='left')

        self._port_var = tk.StringVar()
        self._port_combo = ttk.Combobox(
            self._serial_frame, textvariable=self._port_var,
            width=10, state="readonly"
        )
        self._port_combo.pack(side='left', padx=(4, 0))

        self._refresh_btn = ModernButton(
            self._serial_frame,
            text="\u21BB",
            command=self._refresh_ports,
            width=28,
            height=26,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._refresh_btn.pack(side='left', padx=(4, 0))

        # Connect button
        self._connect_btn = ModernButton(
            conn_frame,
            text="Connect",
            command=self._toggle_connection,
            width=90,
            height=30,
            bg_color=COLORS['btn_primary'],
            font=FONTS['button']
        )
        self._connect_btn.pack(side='left', padx=(12, 0))

        # Status LED
        self._status_led = LEDIndicator(conn_frame, size=12, bg=COLORS['bg_panel'])
        self._status_led.pack(side='left', padx=(8, 0))

        # WiFi config button
        self._wifi_btn = ModernButton(
            conn_frame,
            text="WiFi",
            command=self._configure_wifi,
            width=50,
            height=26,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._wifi_btn.pack(side='left', padx=(8, 0))

        # Test button
        self._test_btn = ModernButton(
            conn_frame,
            text="Test",
            command=self._run_test,
            width=50,
            height=26,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._test_btn.pack(side='left', padx=(4, 0))

        # === Position Display Row ===
        pos_frame = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        pos_frame.pack(fill='x', pady=(10, 0))

        pos_label = tk.Label(
            pos_frame,
            text="Pos:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        pos_label.pack(side='left')

        # Position display
        pos_display_border = tk.Frame(pos_frame, bg=COLORS['border'])
        pos_display_border.pack(side='left', padx=(4, 0))

        pos_display = tk.Frame(pos_display_border, bg=COLORS['bg_display'], padx=8, pady=2)
        pos_display.pack(padx=1, pady=1)

        self._pos_var = tk.StringVar(value="---")
        pos_value = tk.Label(
            pos_display,
            textvariable=self._pos_var,
            font=FONTS['display_small'],
            fg=COLORS['accent_cyan'],
            bg=COLORS['bg_display'],
            width=6
        )
        pos_value.pack(side='left')

        ms_label = tk.Label(
            pos_frame,
            text="ms",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        ms_label.pack(side='left', padx=(4, 0))

        # Mode indicator
        mode_spacer = tk.Frame(pos_frame, bg=COLORS['bg_panel'], width=20)
        mode_spacer.pack(side='left')

        mode_text = tk.Label(
            pos_frame,
            text="Mode:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        mode_text.pack(side='left')

        self._mode_led = LEDIndicator(pos_frame, size=10, bg=COLORS['bg_panel'])
        self._mode_led.pack(side='left', padx=(8, 4))

        self._status_mode_var = tk.StringVar(value="---")
        self._mode_label = tk.Label(
            pos_frame,
            textvariable=self._status_mode_var,
            font=FONTS['subheading'],
            fg=COLORS['status_disabled'],
            bg=COLORS['bg_panel'],
            width=10,
            anchor='w'
        )
        self._mode_label.pack(side='left')

        # === Jog Buttons Row ===
        jog_frame = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        jog_frame.pack(fill='x', pady=(10, 0))
        jog_frame.columnconfigure(0, weight=1)
        jog_frame.columnconfigure(1, weight=1)

        self._jog_up_btn = HoldButton(
            jog_frame,
            text="\u25B2 UP",
            on_press=self._on_jog_up_btn_press_internal,
            on_release=self._on_jog_up_btn_release_internal,
            width=150,
            height=40,
            bg_color=COLORS['btn_up'],
            hover_color=COLORS['btn_up_hover'],
            font=FONTS['button'],
            glow=True,
            glow_color=COLORS['glow_green']
        )
        self._jog_up_btn.grid(row=0, column=0, sticky='ew', padx=(0, 4))

        self._jog_down_btn = HoldButton(
            jog_frame,
            text="\u25BC DOWN",
            on_press=self._on_jog_down_btn_press_internal,
            on_release=self._on_jog_down_btn_release_internal,
            width=150,
            height=40,
            bg_color=COLORS['btn_down'],
            hover_color=COLORS['btn_down_hover'],
            font=FONTS['button'],
            glow=True,
            glow_color=COLORS['glow_orange']
        )
        self._jog_down_btn.grid(row=0, column=1, sticky='ew', padx=(4, 0))

        # === Position Controls Row ===
        ctrl_frame = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        ctrl_frame.pack(fill='x', pady=(8, 0))

        self._go_start_btn = ModernButton(
            ctrl_frame,
            text="GO START",
            command=self._handle_go_start,
            width=90,
            height=32,
            bg_color=COLORS['btn_primary'],
            font=FONTS['button']
        )
        self._go_start_btn.pack(side='left', padx=(0, 4))

        self._go_stop_btn = ModernButton(
            ctrl_frame,
            text="GO STOP",
            command=self._on_go_stop,
            width=90,
            height=32,
            bg_color=COLORS['btn_primary'],
            font=FONTS['button']
        )
        self._go_stop_btn.pack(side='left', padx=4)

        self._stop_btn = ModernButton(
            ctrl_frame,
            text="STOP",
            command=self._handle_stop,
            width=80,
            height=32,
            bg_color=COLORS['btn_danger'],
            hover_color=COLORS['btn_danger_hover'],
            font=FONTS['button'],
            glow=True,
            glow_color=COLORS['glow_red']
        )
        self._stop_btn.pack(side='left', padx=(4, 0))

        # === Save Positions Row ===
        save_frame = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        save_frame.pack(fill='x', pady=(10, 0))

        start_label = tk.Label(
            save_frame,
            text="Start:",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        start_label.pack(side='left')

        self._start_pos_var = tk.StringVar(value="---")
        start_value = tk.Label(
            save_frame,
            textvariable=self._start_pos_var,
            font=FONTS['mono_small'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel'],
            width=6
        )
        start_value.pack(side='left', padx=(4, 0))

        self._save_start_btn = ModernButton(
            save_frame,
            text="Save",
            command=self._on_save_start,
            width=50,
            height=24,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._save_start_btn.pack(side='left', padx=(4, 0))

        # Spacer
        tk.Frame(save_frame, bg=COLORS['bg_panel'], width=20).pack(side='left')

        stop_label = tk.Label(
            save_frame,
            text="Stop:",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        stop_label.pack(side='left')

        self._stop_pos_var = tk.StringVar(value="---")
        stop_value = tk.Label(
            save_frame,
            textvariable=self._stop_pos_var,
            font=FONTS['mono_small'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel'],
            width=6
        )
        stop_value.pack(side='left', padx=(4, 0))

        self._save_stop_btn = ModernButton(
            save_frame,
            text="Save",
            command=self._on_save_stop,
            width=50,
            height=24,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._save_stop_btn.pack(side='left', padx=(4, 0))

        # === Speed/Trim Row ===
        adj_frame = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        adj_frame.pack(fill='x', pady=(10, 0))

        speed_label = tk.Label(
            adj_frame,
            text="Speed:",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        speed_label.pack(side='left')

        self._speed_var = tk.IntVar(value=50)
        self._speed_scale = ModernScale(
            adj_frame,
            from_=10,
            to=100,
            value=50,
            command=self._on_speed_change_internal,
            width=80,
            height=20,
            bg=COLORS['bg_panel']
        )
        self._speed_scale.pack(side='left', padx=(4, 0))

        self._speed_label = tk.Label(
            adj_frame,
            text="50%",
            font=FONTS['small'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel'],
            width=4
        )
        self._speed_label.pack(side='left')

        # Spacer
        tk.Frame(adj_frame, bg=COLORS['bg_panel'], width=20).pack(side='left')

        trim_label = tk.Label(
            adj_frame,
            text="Trim:",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        trim_label.pack(side='left')

        self._trim_var = tk.IntVar(value=0)
        self._trim_spin = ttk.Spinbox(
            adj_frame, from_=-50, to=50, textvariable=self._trim_var,
            width=4, command=self._on_trim_change
        )
        self._trim_spin.pack(side='left', padx=(4, 0))

        us_label = tk.Label(
            adj_frame,
            text="us",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        us_label.pack(side='left', padx=(2, 0))

        # Trim toggle button
        self._trim_toggle_btn = ModernButton(
            adj_frame,
            text="ON",
            command=self._toggle_trim,
            width=40,
            height=22,
            bg_color=COLORS['btn_up'],
            font=FONTS['small']
        )
        self._trim_toggle_btn.pack(side='left', padx=(8, 0))

    def _on_mode_change(self) -> None:
        """Handle mode radio button change."""
        if self._connected:
            self._on_disconnect()

        mode = self._conn_mode_var.get()
        if mode == "wifi":
            self._serial_frame.pack_forget()
            self._wifi_frame.pack(side='left')
        else:
            self._wifi_frame.pack_forget()
            self._serial_frame.pack(side='left')
            self._refresh_ports()

    def _refresh_ports(self) -> None:
        """Refresh the list of available serial ports."""
        ports = self._on_refresh_ports()
        self._port_combo["values"] = ports
        if ports:
            current = self._port_var.get()
            if current not in ports:
                self._port_var.set(ports[0])
        else:
            self._port_var.set("")

    def set_serial_ports(self, ports: List[str]) -> None:
        """Set the available serial ports."""
        self._port_combo["values"] = ports
        if ports:
            current = self._port_var.get()
            if current not in ports:
                self._port_var.set(ports[0])
        else:
            self._port_var.set("")

    def _toggle_connection(self) -> None:
        """Toggle connection based on current mode."""
        if self._connected:
            self._on_disconnect()
        else:
            mode = self._conn_mode_var.get()
            if mode == "wifi":
                ip = self._ip_entry.get().strip()
                if ip:
                    self._on_connect_wifi(ip, 8080)
            else:
                port = self._port_var.get().strip()
                if port:
                    self._on_connect_serial(port, 115200)
                else:
                    messagebox.showwarning("No Port", "Please select a serial port.")

    def _configure_wifi(self) -> None:
        """Open WiFi configuration dialog."""
        WifiConfigDialog(self.winfo_toplevel(), self._on_configure_wifi)

    def _run_test(self) -> None:
        """Run servo test."""
        if self._on_test and self._connected:
            self._on_test()

    def _on_jog_down_btn_press_internal(self) -> None:
        if self._connected:
            self._jog_down_active = True
            self._on_jog_down_press()

    def _on_jog_down_btn_release_internal(self) -> None:
        if self._jog_down_active:
            self._jog_down_active = False
            self._on_jog_down_release()

    def _on_jog_up_btn_press_internal(self) -> None:
        if self._connected:
            self._jog_up_active = True
            self._restore_trim_if_needed()
            self._on_jog_up_press()

    def _on_jog_up_btn_release_internal(self) -> None:
        if self._jog_up_active:
            self._jog_up_active = False
            self._on_jog_up_release()

    def _restore_trim_if_needed(self) -> None:
        """Restore trim to saved value if it was zeroed by stop."""
        if self._trim_zeroed and self._connected:
            self._on_set_trim(self._saved_trim_value)
            self._trim_var.set(self._saved_trim_value)
            self._trim_zeroed = False
            self._update_trim_button()

    def _zero_trim_for_stop(self) -> None:
        """Zero the trim when stopping."""
        if self._connected and not self._trim_zeroed:
            self._saved_trim_value = self._trim_var.get()
            self._on_set_trim(0)
            self._trim_var.set(0)
            self._trim_zeroed = True
            self._update_trim_button()

    def _handle_stop(self) -> None:
        """Handle STOP button."""
        self._zero_trim_for_stop()
        self._on_stop()

    def _handle_go_start(self) -> None:
        """Handle GO START button."""
        self._restore_trim_if_needed()
        self._on_go_start()

    def _toggle_trim(self) -> None:
        """Toggle trim on/off."""
        if self._trim_zeroed:
            self._restore_trim_if_needed()
        else:
            self._zero_trim_for_stop()
        self._update_trim_button()

    def _update_trim_button(self) -> None:
        """Update trim toggle button appearance."""
        if self._trim_zeroed:
            self._trim_toggle_btn.set_text("OFF")
            self._trim_toggle_btn.configure_colors(bg_color=COLORS['btn_danger'])
        else:
            self._trim_toggle_btn.set_text("ON")
            self._trim_toggle_btn.configure_colors(bg_color=COLORS['btn_up'])

    def _on_speed_change_internal(self, value: float) -> None:
        speed = int(value)
        self._speed_var.set(speed)
        self._speed_label.config(text=f"{speed}%")
        if self._connected:
            self._on_set_speed(speed)

    def _on_trim_change(self) -> None:
        if self._connected:
            trim_value = self._trim_var.get()
            self._saved_trim_value = trim_value
            self._trim_zeroed = False
            self._update_trim_button()
            self._on_set_trim(trim_value)

    def set_connection_state(self, state: WifiConnectionState, connected: bool, mode: Optional[ConnectionMode] = None) -> None:
        """Update connection state display."""
        self._connected = connected
        self._connection_mode = mode

        # Update LED
        if state == WifiConnectionState.DISCONNECTED:
            self._status_led.set_state('disconnected')
        elif state == WifiConnectionState.CONNECTING:
            self._status_led.set_state('connecting')
        elif state == WifiConnectionState.CONNECTED:
            self._status_led.set_state('connected')
        else:
            self._status_led.set_state('error')

        # Update connect button
        if connected:
            self._connect_btn.set_text("Disconnect")
            self._connect_btn.configure_colors(bg_color=COLORS['btn_danger'])
        else:
            self._connect_btn.set_text("Connect")
            self._connect_btn.configure_colors(bg_color=COLORS['btn_primary'])

        # Disable inputs when connected
        self._ip_entry.set_enabled(not connected)
        port_state = "disabled" if connected else "readonly"
        self._port_combo.config(state=port_state)
        self._refresh_btn.set_enabled(not connected)

        # Disable mode switching while connected
        radio_state = "disabled" if connected else "normal"
        self._wifi_radio.config(state=radio_state)
        self._serial_radio.config(state=radio_state)

    def update_status(self, status: Optional[DropCylinderStatus]) -> None:
        """Update display with new status."""
        if status is None:
            self._pos_var.set("---")
            self._status_mode_var.set("---")
            self._mode_led.set_state('disabled')
            self._mode_label.config(fg=COLORS['status_disabled'])
            self._start_pos_var.set("---")
            self._stop_pos_var.set("---")
            return

        self._pos_var.set(f"{status.position_ms}")

        mode_states = {
            "IDLE": ('idle', COLORS['status_idle']),
            "JOG_DOWN": ('jog', COLORS['status_jog']),
            "JOG_UP": ('idle', COLORS['status_idle']),
            "MOVE_START": ('move', COLORS['status_move']),
            "MOVE_STOP": ('move', COLORS['status_move'])
        }
        led_state, mode_color = mode_states.get(status.mode, ('disabled', COLORS['status_disabled']))
        self._status_mode_var.set(status.mode)
        self._mode_led.set_state(led_state)
        self._mode_label.config(fg=mode_color)

        if status.start_saved and status.start_position_ms is not None:
            self._start_pos_var.set(f"{status.start_position_ms}")
        else:
            self._start_pos_var.set("---")

        if status.stop_saved and status.stop_position_ms is not None:
            self._stop_pos_var.set(f"{status.stop_position_ms}")
        else:
            self._stop_pos_var.set("---")

        if not self._trim_zeroed:
            self._saved_trim_value = status.trim_us
        self._trim_var.set(status.trim_us)
        self._speed_var.set(status.speed_percent)
        self._speed_scale.set(status.speed_percent)
        self._speed_label.config(text=f"{status.speed_percent}%")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable controls."""
        self._jog_up_btn.set_enabled(enabled)
        self._jog_down_btn.set_enabled(enabled)
        self._stop_btn.set_enabled(enabled)
        self._go_start_btn.set_enabled(enabled)
        self._go_stop_btn.set_enabled(enabled)
        self._speed_scale.set_enabled(enabled)


class WifiConfigDialog(tk.Toplevel):
    """Dialog for configuring ESP32 WiFi credentials."""

    def __init__(self, parent: tk.Widget, on_save: Callable[[str, str], None]):
        super().__init__(parent)
        self._on_save = on_save

        self.title("Configure ESP32 WiFi")
        self.configure(bg=COLORS['bg_dark'])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        # Border frame
        border = tk.Frame(self, bg=COLORS['border'])
        border.pack(fill='both', expand=True, padx=1, pady=1)

        frame = tk.Frame(border, bg=COLORS['bg_panel'], padx=20, pady=15)
        frame.pack(fill='both', expand=True)

        # Header
        header = tk.Label(
            frame,
            text="Configure ESP32 WiFi",
            font=FONTS['heading'],
            fg=COLORS['text_accent'],
            bg=COLORS['bg_panel']
        )
        header.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 8))

        info = tk.Label(
            frame,
            text="Configure the ESP32 to connect to your WiFi network.\nAfter saving, the ESP32 will restart and connect.",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel'],
            justify='left'
        )
        info.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 12))

        # SSID
        ssid_label = tk.Label(
            frame,
            text="SSID:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        ssid_label.grid(row=2, column=0, sticky='e', pady=4, padx=(0, 8))

        self._ssid_entry = ModernEntry(frame, width=25)
        self._ssid_entry.grid(row=2, column=1, sticky='w', pady=4)

        # Password
        pass_label = tk.Label(
            frame,
            text="Password:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        pass_label.grid(row=3, column=0, sticky='e', pady=4, padx=(0, 8))

        self._pass_entry = ModernEntry(frame, width=25)
        self._pass_entry.configure(show="*")
        self._pass_entry.grid(row=3, column=1, sticky='w', pady=4)

        # Buttons
        btn_frame = tk.Frame(frame, bg=COLORS['bg_panel'])
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(16, 0))

        save_btn = ModernButton(
            btn_frame,
            text="Save & Restart",
            command=self._save,
            width=120,
            height=32,
            bg_color=COLORS['btn_primary'],
            font=FONTS['button']
        )
        save_btn.pack(side='left', padx=(0, 8))

        cancel_btn = ModernButton(
            btn_frame,
            text="Cancel",
            command=self.destroy,
            width=80,
            height=32,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['button']
        )
        cancel_btn.pack(side='left')

    def _save(self) -> None:
        ssid = self._ssid_entry.get().strip()
        password = self._pass_entry.get()

        if not ssid:
            messagebox.showwarning("Invalid", "Please enter SSID")
            return

        self._on_save(ssid, password)
        self.destroy()
