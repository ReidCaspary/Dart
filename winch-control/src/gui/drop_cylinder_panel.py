"""
Drop Cylinder Control Panel

Controls for the ESP32-based servo winch drop cylinder system.
Supports both WiFi and USB serial connections.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Callable, Optional, List

from ..wifi_manager import DropCylinderStatus, WifiConnectionState, ConnectionMode


class DropCylinderPanel(ttk.LabelFrame):
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
        super().__init__(parent, text="Drop Cylinder", padding=5)

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

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create panel widgets."""
        self.columnconfigure(0, weight=1)

        # Mode selection row
        mode_frame = ttk.Frame(self)
        mode_frame.grid(row=0, column=0, sticky="ew", pady=2)

        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT)

        self._conn_mode_var = tk.StringVar(value="wifi")
        self._wifi_radio = ttk.Radiobutton(
            mode_frame, text="WiFi", variable=self._conn_mode_var,
            value="wifi", command=self._on_mode_change
        )
        self._wifi_radio.pack(side=tk.LEFT, padx=(5, 2))

        self._serial_radio = ttk.Radiobutton(
            mode_frame, text="Serial", variable=self._conn_mode_var,
            value="serial", command=self._on_mode_change
        )
        self._serial_radio.pack(side=tk.LEFT, padx=2)

        # Connection row
        conn_frame = ttk.Frame(self)
        conn_frame.grid(row=1, column=0, sticky="ew", pady=2)

        # WiFi widgets (IP entry)
        self._wifi_frame = ttk.Frame(conn_frame)
        self._wifi_frame.pack(side=tk.LEFT)

        ttk.Label(self._wifi_frame, text="IP:").pack(side=tk.LEFT)
        self._ip_var = tk.StringVar(value="192.168.4.1")  # Default AP IP
        self._ip_entry = ttk.Entry(self._wifi_frame, textvariable=self._ip_var, width=14)
        self._ip_entry.pack(side=tk.LEFT, padx=2)

        # Serial widgets (port combobox and refresh button)
        self._serial_frame = ttk.Frame(conn_frame)
        # Serial frame is not packed initially - will be shown when serial mode is selected

        ttk.Label(self._serial_frame, text="Port:").pack(side=tk.LEFT)
        self._port_var = tk.StringVar()
        self._port_combo = ttk.Combobox(
            self._serial_frame, textvariable=self._port_var,
            width=10, state="readonly"
        )
        self._port_combo.pack(side=tk.LEFT, padx=2)

        self._refresh_btn = ttk.Button(
            self._serial_frame, text="\u21BB", width=2,
            command=self._refresh_ports
        )
        self._refresh_btn.pack(side=tk.LEFT)

        # Connect button
        self._connect_btn = ttk.Button(conn_frame, text="Connect", command=self._toggle_connection, width=8)
        self._connect_btn.pack(side=tk.LEFT, padx=2)

        # Connection status indicator
        self._status_canvas = tk.Canvas(conn_frame, width=12, height=12, highlightthickness=0)
        self._status_canvas.pack(side=tk.LEFT, padx=2)
        self._status_oval = self._status_canvas.create_oval(1, 1, 11, 11, fill="gray")

        # WiFi config button
        self._wifi_btn = ttk.Button(conn_frame, text="WiFi", command=self._configure_wifi, width=4)
        self._wifi_btn.pack(side=tk.LEFT, padx=2)

        # Test button
        self._test_btn = ttk.Button(conn_frame, text="Test", command=self._run_test, width=4)
        self._test_btn.pack(side=tk.LEFT, padx=2)

        # Position display
        pos_frame = ttk.Frame(self)
        pos_frame.grid(row=2, column=0, sticky="ew", pady=2)

        ttk.Label(pos_frame, text="Pos:", font=("Arial", 9)).pack(side=tk.LEFT)
        self._pos_var = tk.StringVar(value="---")
        ttk.Label(pos_frame, textvariable=self._pos_var, font=("Consolas", 11), width=8).pack(side=tk.LEFT)
        ttk.Label(pos_frame, text="ms", font=("Arial", 8)).pack(side=tk.LEFT)

        ttk.Label(pos_frame, text="Mode:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(10, 0))
        self._status_mode_var = tk.StringVar(value="---")
        self._mode_label = tk.Label(pos_frame, textvariable=self._status_mode_var, font=("Arial", 9, "bold"),
                                     bg="gray", fg="white", width=10, pady=1)
        self._mode_label.pack(side=tk.LEFT, padx=2)

        # Jog buttons
        jog_frame = ttk.Frame(self)
        jog_frame.grid(row=3, column=0, sticky="ew", pady=2)
        jog_frame.columnconfigure(0, weight=1)
        jog_frame.columnconfigure(1, weight=1)

        self._jog_up_btn = tk.Button(
            jog_frame, text="\u25B2 UP", font=("Arial", 10, "bold"),
            bg="#4CAF50", fg="white", activebackground="#388E3C"
        )
        self._jog_up_btn.grid(row=0, column=0, sticky="ew", padx=1, ipady=3)
        self._jog_up_btn.bind("<ButtonPress-1>", self._on_jog_up_btn_press)
        self._jog_up_btn.bind("<ButtonRelease-1>", self._on_jog_up_btn_release)

        self._jog_down_btn = tk.Button(
            jog_frame, text="\u25BC DOWN", font=("Arial", 10, "bold"),
            bg="#FF9800", fg="white", activebackground="#F57C00"
        )
        self._jog_down_btn.grid(row=0, column=1, sticky="ew", padx=1, ipady=3)
        self._jog_down_btn.bind("<ButtonPress-1>", self._on_jog_down_btn_press)
        self._jog_down_btn.bind("<ButtonRelease-1>", self._on_jog_down_btn_release)

        # Position controls
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.grid(row=4, column=0, sticky="ew", pady=2)

        ttk.Button(ctrl_frame, text="GO START", command=self._on_go_start, width=9).pack(side=tk.LEFT, padx=1)
        ttk.Button(ctrl_frame, text="GO STOP", command=self._on_go_stop, width=9).pack(side=tk.LEFT, padx=1)

        self._stop_btn = tk.Button(
            ctrl_frame, text="STOP", font=("Arial", 9, "bold"),
            bg="#D32F2F", fg="white", command=self._on_stop, width=6
        )
        self._stop_btn.pack(side=tk.LEFT, padx=1)

        # Save positions
        save_frame = ttk.Frame(self)
        save_frame.grid(row=5, column=0, sticky="ew", pady=2)

        ttk.Label(save_frame, text="Start:", font=("Arial", 8)).pack(side=tk.LEFT)
        self._start_pos_var = tk.StringVar(value="---")
        ttk.Label(save_frame, textvariable=self._start_pos_var, font=("Consolas", 8), width=6).pack(side=tk.LEFT)
        ttk.Button(save_frame, text="Save", command=self._on_save_start, width=4).pack(side=tk.LEFT, padx=2)

        ttk.Label(save_frame, text="Stop:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(5, 0))
        self._stop_pos_var = tk.StringVar(value="---")
        ttk.Label(save_frame, textvariable=self._stop_pos_var, font=("Consolas", 8), width=6).pack(side=tk.LEFT)
        ttk.Button(save_frame, text="Save", command=self._on_save_stop, width=4).pack(side=tk.LEFT, padx=2)

        # Speed/Trim controls
        adj_frame = ttk.Frame(self)
        adj_frame.grid(row=6, column=0, sticky="ew", pady=2)

        ttk.Label(adj_frame, text="Speed:", font=("Arial", 8)).pack(side=tk.LEFT)
        self._speed_var = tk.IntVar(value=50)
        self._speed_scale = ttk.Scale(adj_frame, from_=10, to=100, variable=self._speed_var,
                                       orient=tk.HORIZONTAL, length=60, command=self._on_speed_change)
        self._speed_scale.pack(side=tk.LEFT, padx=2)
        self._speed_label = ttk.Label(adj_frame, text="50%", font=("Arial", 8), width=4)
        self._speed_label.pack(side=tk.LEFT)

        ttk.Label(adj_frame, text="Trim:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(10, 0))
        self._trim_var = tk.IntVar(value=0)
        self._trim_spin = ttk.Spinbox(adj_frame, from_=-50, to=50, textvariable=self._trim_var,
                                       width=4, command=self._on_trim_change)
        self._trim_spin.pack(side=tk.LEFT, padx=2)
        ttk.Label(adj_frame, text="us", font=("Arial", 8)).pack(side=tk.LEFT)

    def _on_mode_change(self) -> None:
        """Handle mode radio button change."""
        # If connected, disconnect first
        if self._connected:
            self._on_disconnect()

        mode = self._conn_mode_var.get()
        if mode == "wifi":
            self._serial_frame.pack_forget()
            self._wifi_frame.pack(side=tk.LEFT)
        else:
            self._wifi_frame.pack_forget()
            self._serial_frame.pack(side=tk.LEFT)
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
                ip = self._ip_var.get().strip()
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
        dialog = WifiConfigDialog(self.winfo_toplevel(), self._on_configure_wifi)

    def _run_test(self) -> None:
        """Run servo test."""
        if self._on_test and self._connected:
            self._on_test()

    def _on_jog_down_btn_press(self, event: tk.Event) -> None:
        if not self._jog_down_active and self._connected:
            self._jog_down_active = True
            self._jog_down_btn.configure(relief=tk.SUNKEN)
            self._on_jog_down_press()

    def _on_jog_down_btn_release(self, event: tk.Event) -> None:
        if self._jog_down_active:
            self._jog_down_active = False
            self._jog_down_btn.configure(relief=tk.RAISED)
            self._on_jog_down_release()

    def _on_jog_up_btn_press(self, event: tk.Event) -> None:
        if not self._jog_up_active and self._connected:
            self._jog_up_active = True
            self._jog_up_btn.configure(relief=tk.SUNKEN)
            self._on_jog_up_press()

    def _on_jog_up_btn_release(self, event: tk.Event) -> None:
        if self._jog_up_active:
            self._jog_up_active = False
            self._jog_up_btn.configure(relief=tk.RAISED)
            self._on_jog_up_release()

    def _on_speed_change(self, value: str) -> None:
        speed = int(float(value))
        self._speed_label.config(text=f"{speed}%")
        if self._connected:
            self._on_set_speed(speed)

    def _on_trim_change(self) -> None:
        if self._connected:
            self._on_set_trim(self._trim_var.get())

    def set_connection_state(self, state: WifiConnectionState, connected: bool, mode: Optional[ConnectionMode] = None) -> None:
        """Update connection state display."""
        self._connected = connected
        self._connection_mode = mode
        colors = {
            WifiConnectionState.DISCONNECTED: "gray",
            WifiConnectionState.CONNECTING: "yellow",
            WifiConnectionState.CONNECTED: "#4CAF50",
            WifiConnectionState.ERROR: "red"
        }
        self._status_canvas.itemconfig(self._status_oval, fill=colors.get(state, "gray"))
        self._connect_btn.config(text="Disconnect" if connected else "Connect")

        # Disable appropriate input based on connection state
        self._ip_entry.config(state="disabled" if connected else "normal")
        port_state = "disabled" if connected else "readonly"
        self._port_combo.config(state=port_state)
        self._refresh_btn.config(state="disabled" if connected else "normal")

        # Disable mode switching while connected
        radio_state = "disabled" if connected else "normal"
        self._wifi_radio.config(state=radio_state)
        self._serial_radio.config(state=radio_state)

    def update_status(self, status: Optional[DropCylinderStatus]) -> None:
        """Update display with new status."""
        if status is None:
            self._pos_var.set("---")
            self._status_mode_var.set("---")
            self._mode_label.config(bg="gray")
            self._start_pos_var.set("---")
            self._stop_pos_var.set("---")
            return

        self._pos_var.set(f"{status.position_ms}")

        mode_colors = {
            "IDLE": "#757575",
            "JOG_DOWN": "#FF9800",
            "JOG_UP": "#4CAF50",
            "MOVE_START": "#2196F3",
            "MOVE_STOP": "#2196F3"
        }
        self._status_mode_var.set(status.mode)
        self._mode_label.config(bg=mode_colors.get(status.mode, "gray"))

        if status.start_saved and status.start_position_ms is not None:
            self._start_pos_var.set(f"{status.start_position_ms}")
        else:
            self._start_pos_var.set("---")

        if status.stop_saved and status.stop_position_ms is not None:
            self._stop_pos_var.set(f"{status.stop_position_ms}")
        else:
            self._stop_pos_var.set("---")

        self._trim_var.set(status.trim_us)
        self._speed_var.set(status.speed_percent)
        self._speed_label.config(text=f"{status.speed_percent}%")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable controls."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self._jog_up_btn.config(state=state)
        self._jog_down_btn.config(state=state)
        self._stop_btn.config(state=state)


class WifiConfigDialog(tk.Toplevel):
    """Dialog for configuring ESP32 WiFi credentials."""

    def __init__(self, parent: tk.Widget, on_save: Callable[[str, str], None]):
        super().__init__(parent)
        self._on_save = on_save

        self.title("Configure ESP32 WiFi")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Configure the ESP32 to connect to your WiFi network.\n"
                             "After saving, the ESP32 will restart and connect.",
                  font=("Arial", 9), foreground="gray").grid(row=0, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(frame, text="SSID:").grid(row=1, column=0, sticky="e", pady=5)
        self._ssid_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._ssid_var, width=25).grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="Password:").grid(row=2, column=0, sticky="e", pady=5)
        self._pass_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._pass_var, width=25, show="*").grid(row=2, column=1, pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(btn_frame, text="Save & Restart ESP32", command=self._save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _save(self) -> None:
        ssid = self._ssid_var.get().strip()
        password = self._pass_var.get()

        if not ssid:
            messagebox.showwarning("Invalid", "Please enter SSID")
            return

        self._on_save(ssid, password)
        self.destroy()
