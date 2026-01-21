"""
Status Bar

Shows connection status, E-stop indicator, and communication info.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional

from ..serial_manager import ConnectionState


class StatusBar(ttk.Frame):
    """
    Status bar showing connection info and E-stop indicator.

    Features:
    - E-stop warning banner (prominent when active)
    - Connection status indicator
    - Last command sent
    - Last response received
    - Last communication timestamp
    """

    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout status bar widgets."""
        self.columnconfigure(0, weight=1)

        # E-STOP Warning Banner (hidden by default)
        self._estop_frame = tk.Frame(self, bg="#D32F2F", height=25)
        self._estop_label = tk.Label(
            self._estop_frame,
            text="\u26A0 E-STOP ACTIVE \u26A0",
            font=("Arial", 12, "bold"),
            bg="#D32F2F",
            fg="white",
            pady=2
        )
        self._estop_label.pack(expand=True, fill=tk.BOTH)
        self._estop_visible = False

        # Single row status frame
        status_frame = ttk.Frame(self)
        status_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)

        # Connection indicator
        self._status_indicator = tk.Canvas(status_frame, width=12, height=12, highlightthickness=0)
        self._status_indicator.pack(side=tk.LEFT)
        self._indicator_oval = self._status_indicator.create_oval(1, 1, 11, 11, fill="gray", outline="darkgray")

        self._status_text_var = tk.StringVar(value="Disconnected")
        ttk.Label(status_frame, textvariable=self._status_text_var, font=("Arial", 8)).pack(side=tk.LEFT, padx=(3, 10))

        # Last comm time
        ttk.Label(status_frame, text="Last:", font=("Arial", 8)).pack(side=tk.LEFT)
        self._last_comm_var = tk.StringVar(value="---")
        ttk.Label(status_frame, textvariable=self._last_comm_var, font=("Consolas", 8)).pack(side=tk.LEFT, padx=(2, 10))

        # Last command
        ttk.Label(status_frame, text="Tx:", font=("Arial", 8)).pack(side=tk.LEFT)
        self._last_cmd_var = tk.StringVar(value="---")
        ttk.Label(status_frame, textvariable=self._last_cmd_var, font=("Consolas", 8), foreground="blue").pack(side=tk.LEFT, padx=(2, 10))

        # Last response
        ttk.Label(status_frame, text="Rx:", font=("Arial", 8)).pack(side=tk.LEFT)
        self._last_resp_var = tk.StringVar(value="---")
        self._last_resp_label = ttk.Label(status_frame, textvariable=self._last_resp_var, font=("Consolas", 7), foreground="green")
        self._last_resp_label.pack(side=tk.LEFT, padx=(2, 0))

    def set_connection_state(self, state: ConnectionState, message: str = "") -> None:
        """
        Update connection status indicator.

        Args:
            state: Current connection state
            message: Optional status message
        """
        colors = {
            ConnectionState.DISCONNECTED: ("gray", "Disconnected"),
            ConnectionState.CONNECTING: ("yellow", "Connecting..."),
            ConnectionState.CONNECTED: ("#4CAF50", "Connected"),
            ConnectionState.ERROR: ("red", "Error")
        }

        color, default_text = colors.get(state, ("gray", "Unknown"))
        self._status_indicator.itemconfig(self._indicator_oval, fill=color)
        self._status_text_var.set(message if message else default_text)

    def set_estop_active(self, active: bool) -> None:
        """
        Show or hide E-stop warning banner.

        Args:
            active: True to show warning, False to hide
        """
        if active and not self._estop_visible:
            self._estop_frame.grid(row=0, column=0, sticky="ew")
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
        if len(response) > 80:
            response = response[:77] + "..."
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
