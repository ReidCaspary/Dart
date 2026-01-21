"""
Settings Panel

Contains position save buttons and saved position displays.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class SettingsPanel(ttk.Frame):
    """
    Settings panel for saving and displaying home/well positions.

    Features:
    - Save Home / Save Well buttons
    - Display of saved positions
    - Zero Position button
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_save_home: Callable[[], None],
        on_save_well: Callable[[], None],
        on_zero_position: Callable[[], None]
    ):
        super().__init__(parent)

        self._on_save_home = on_save_home
        self._on_save_well = on_save_well
        self._on_zero_position = on_zero_position

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout settings widgets."""
        self.columnconfigure(0, weight=1)

        # Main settings frame - compact single row layout
        settings_frame = ttk.LabelFrame(self, text="Saved Positions", padding=5)
        settings_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(4, weight=1)

        # Home: label, value, save button
        ttk.Label(settings_frame, text="Home:", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=2)
        self._home_pos_var = tk.StringVar(value="Not Set")
        self._home_pos_label = ttk.Label(settings_frame, textvariable=self._home_pos_var, font=("Consolas", 9), foreground="gray", width=12)
        self._home_pos_label.grid(row=0, column=1, sticky="w", padx=2)
        self._save_home_btn = ttk.Button(settings_frame, text="SAVE", command=self._on_save_home, width=6)
        self._save_home_btn.grid(row=0, column=2, padx=2)

        # Well: label, value, save button
        ttk.Label(settings_frame, text="Well:", font=("Arial", 9, "bold")).grid(row=0, column=3, padx=(10, 2))
        self._well_pos_var = tk.StringVar(value="Not Set")
        self._well_pos_label = ttk.Label(settings_frame, textvariable=self._well_pos_var, font=("Consolas", 9), foreground="gray", width=12)
        self._well_pos_label.grid(row=0, column=4, sticky="w", padx=2)
        self._save_well_btn = ttk.Button(settings_frame, text="SAVE", command=self._on_save_well, width=6)
        self._save_well_btn.grid(row=0, column=5, padx=2)

        # Zero button
        self._zero_btn = ttk.Button(settings_frame, text="ZERO", command=self._on_zero_position, width=6)
        self._zero_btn.grid(row=0, column=6, padx=(10, 2))

    def update_home_position(self, saved: bool, position: Optional[int]) -> None:
        """
        Update home position display.

        Args:
            saved: Whether home position is saved
            position: Home position in steps (or None)
        """
        if saved and position is not None:
            self._home_pos_var.set(f"{position:,} steps")
            self._home_pos_label.configure(foreground="black")
        else:
            self._home_pos_var.set("Not Set")
            self._home_pos_label.configure(foreground="gray")

    def update_well_position(self, saved: bool, position: Optional[int]) -> None:
        """
        Update well position display.

        Args:
            saved: Whether well position is saved
            position: Well position in steps (or None)
        """
        if saved and position is not None:
            self._well_pos_var.set(f"{position:,} steps")
            self._well_pos_label.configure(foreground="black")
        else:
            self._well_pos_var.set("Not Set")
            self._well_pos_label.configure(foreground="gray")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all controls."""
        state = "normal" if enabled else "disabled"
        self._save_home_btn.configure(state=state)
        self._save_well_btn.configure(state=state)
        self._zero_btn.configure(state=state)
