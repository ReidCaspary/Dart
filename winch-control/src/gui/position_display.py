"""
Position Display Panel

Shows current position, speed, and motion mode with prominent display.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..command_protocol import WinchStatus, MotionMode


# Color scheme for motion modes
MODE_COLORS = {
    MotionMode.IDLE: "#2E7D32",   # Green
    MotionMode.JOG: "#F57C00",    # Orange
    MotionMode.MOVE: "#1976D2",   # Blue
    MotionMode.UNKNOWN: "#757575" # Gray
}


class PositionDisplay(ttk.Frame):
    """
    Widget displaying current position, speed, and motion mode.

    Features:
    - Large numeric position display in steps
    - Position converted to revolutions
    - Current speed in RPS
    - Color-coded motion mode indicator
    """

    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout display widgets."""
        # Configure frame
        self.columnconfigure(0, weight=1)

        # Combined position/speed/mode in one row
        main_frame = ttk.LabelFrame(self, text="Status", padding=5)
        main_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.columnconfigure(2, weight=0)

        # Position display (left side)
        pos_frame = ttk.Frame(main_frame)
        pos_frame.grid(row=0, column=0, sticky="w")

        self._position_var = tk.StringVar(value="---")
        self._position_label = tk.Label(
            pos_frame,
            textvariable=self._position_var,
            font=("Consolas", 28, "bold"),
            bg="#1a1a1a",
            fg="#00ff00",
            padx=10,
            pady=5
        )
        self._position_label.pack(side=tk.LEFT)

        unit_frame = ttk.Frame(pos_frame)
        unit_frame.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(unit_frame, text="steps", font=("Arial", 9)).pack(anchor="w")
        self._revolutions_var = tk.StringVar(value="---")
        rev_label = ttk.Label(unit_frame, textvariable=self._revolutions_var, font=("Consolas", 10))
        rev_label.pack(anchor="w")

        # Speed display (middle)
        speed_frame = ttk.Frame(main_frame)
        speed_frame.grid(row=0, column=1, padx=10)
        ttk.Label(speed_frame, text="Speed", font=("Arial", 9)).pack()
        self._speed_var = tk.StringVar(value="0.00")
        ttk.Label(speed_frame, textvariable=self._speed_var, font=("Consolas", 16)).pack()
        ttk.Label(speed_frame, text="RPS", font=("Arial", 8)).pack()

        # Mode display (right)
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=0, column=2, padx=(10, 0))
        ttk.Label(mode_frame, text="Mode", font=("Arial", 9)).pack()
        self._mode_var = tk.StringVar(value="---")
        self._mode_label = tk.Label(
            mode_frame,
            textvariable=self._mode_var,
            font=("Arial", 12, "bold"),
            width=8,
            bg=MODE_COLORS[MotionMode.UNKNOWN],
            fg="white",
            pady=2
        )
        self._mode_label.pack()

    def update_status(self, status: Optional[WinchStatus]) -> None:
        """
        Update display with new status data.

        Args:
            status: WinchStatus object or None to show disconnected state
        """
        if status is None:
            self._position_var.set("---")
            self._revolutions_var.set("---")
            self._speed_var.set("---")
            self._mode_var.set("---")
            self._mode_label.configure(bg=MODE_COLORS[MotionMode.UNKNOWN])
            self._position_label.configure(fg="#666666")
            return

        # Update position
        self._position_var.set(f"{status.position:,}")
        self._revolutions_var.set(f"{status.position_revolutions:.3f}")

        # Update speed
        self._speed_var.set(f"{status.speed_rps:.2f}")

        # Update mode with color
        self._mode_var.set(status.mode.value)
        self._mode_label.configure(bg=MODE_COLORS.get(status.mode, MODE_COLORS[MotionMode.UNKNOWN]))

        # Position color based on mode
        if status.mode == MotionMode.IDLE:
            self._position_label.configure(fg="#00ff00")  # Green
        elif status.mode == MotionMode.JOG:
            self._position_label.configure(fg="#ffaa00")  # Orange
        else:
            self._position_label.configure(fg="#00aaff")  # Blue

    def set_disconnected(self) -> None:
        """Show disconnected state."""
        self.update_status(None)
