"""
Status Bar

Shows connection status, E-stop indicator, and communication info.
Modern dark theme styling with LED indicators.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional

from ..serial_manager import ConnectionState
from .theme import COLORS, FONTS
from .widgets import LEDIndicator


class StatusBar(tk.Frame):
    """
    Status bar showing connection info and E-stop indicator.

    Features:
    - E-stop warning banner (prominent when active)
    - LED-style connection status indicator
    - Last command sent
    - Last response received
    - Last communication timestamp
    """

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, bg=COLORS['bg_dark'])
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout status bar widgets."""
        self.columnconfigure(0, weight=1)

        # E-STOP Warning Banner (hidden by default)
        self._estop_frame = tk.Frame(self, bg=COLORS['status_error'], height=30)
        self._estop_label = tk.Label(
            self._estop_frame,
            text="\u26A0 E-STOP ACTIVE \u26A0",
            font=FONTS['button_large'],
            bg=COLORS['status_error'],
            fg='white',
            pady=4
        )
        self._estop_label.pack(expand=True, fill='both')
        self._estop_visible = False

        # Main status panel
        panel_border = tk.Frame(self, bg=COLORS['border'])
        panel_border.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

        status_frame = tk.Frame(panel_border, bg=COLORS['bg_panel'], padx=12, pady=8)
        status_frame.pack(fill='x', padx=1, pady=1)

        # Connection indicator LED
        self._status_led = LEDIndicator(status_frame, size=10, bg=COLORS['bg_panel'])
        self._status_led.pack(side='left')

        # Connection status text
        self._status_text_var = tk.StringVar(value="Disconnected")
        status_text = tk.Label(
            status_frame,
            textvariable=self._status_text_var,
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        status_text.pack(side='left', padx=(6, 16))

        # Last comm time
        last_label = tk.Label(
            status_frame,
            text="Last:",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        last_label.pack(side='left')

        self._last_comm_var = tk.StringVar(value="---")
        last_value = tk.Label(
            status_frame,
            textvariable=self._last_comm_var,
            font=FONTS['mono_small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        last_value.pack(side='left', padx=(4, 16))

        # Last command (Tx)
        tx_label = tk.Label(
            status_frame,
            text="Tx:",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        tx_label.pack(side='left')

        self._last_cmd_var = tk.StringVar(value="---")
        tx_value = tk.Label(
            status_frame,
            textvariable=self._last_cmd_var,
            font=FONTS['mono_small'],
            fg=COLORS['accent_cyan'],
            bg=COLORS['bg_panel']
        )
        tx_value.pack(side='left', padx=(4, 16))

        # Last response (Rx)
        rx_label = tk.Label(
            status_frame,
            text="Rx:",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        rx_label.pack(side='left')

        self._last_resp_var = tk.StringVar(value="---")
        rx_value = tk.Label(
            status_frame,
            textvariable=self._last_resp_var,
            font=FONTS['mono_small'],
            fg=COLORS['accent_green'],
            bg=COLORS['bg_panel']
        )
        rx_value.pack(side='left', padx=(4, 0))

    def set_connection_state(self, state: ConnectionState, message: str = "") -> None:
        """
        Update connection status indicator.

        Args:
            state: Current connection state
            message: Optional status message
        """
        state_map = {
            ConnectionState.DISCONNECTED: ('disconnected', "Disconnected"),
            ConnectionState.CONNECTING: ('connecting', "Connecting..."),
            ConnectionState.CONNECTED: ('connected', "Connected"),
            ConnectionState.ERROR: ('error', "Error")
        }

        led_state, default_text = state_map.get(state, ('disconnected', "Unknown"))
        self._status_led.set_state(led_state)
        self._status_text_var.set(message if message else default_text)

    def set_estop_active(self, active: bool) -> None:
        """
        Show or hide E-stop warning banner.

        Args:
            active: True to show warning, False to hide
        """
        if active and not self._estop_visible:
            self._estop_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
            self._estop_visible = True
        elif not active and self._estop_visible:
            self._estop_frame.grid_forget()
            self._estop_visible = False

    def set_last_command(self, command: str) -> None:
        """Update last command sent display."""
        self._last_cmd_var.set(command if command else "---")

    def set_last_response(self, response: str) -> None:
        """Update last response received display."""
        # Truncate if too long
        if len(response) > 60:
            response = response[:57] + "..."
        self._last_resp_var.set(response if response else "---")

    def set_last_comm_time(self, timestamp: Optional[float]) -> None:
        """
        Update last communication timestamp.

        Args:
            timestamp: Unix timestamp or None
        """
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            self._last_comm_var.set(dt.strftime("%H:%M:%S"))
        else:
            self._last_comm_var.set("---")
