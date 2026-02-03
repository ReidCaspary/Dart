"""
Settings Panel

Contains position save buttons and saved position displays.
Modern dark theme styling.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import COLORS, FONTS
from .widgets import ModernButton


class SettingsPanel(tk.Frame):
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
        on_zero_position: Callable[[], None],
        on_clear_fault: Callable[[], None] = None
    ):
        super().__init__(parent, bg=COLORS['bg_dark'])

        self._on_save_home = on_save_home
        self._on_save_well = on_save_well
        self._on_zero_position = on_zero_position
        self._on_clear_fault = on_clear_fault

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout settings widgets."""
        self.columnconfigure(0, weight=1)

        # Panel border
        panel_border = tk.Frame(self, bg=COLORS['border'])
        panel_border.grid(row=0, column=0, sticky="ew", padx=8, pady=4)

        panel_frame = tk.Frame(panel_border, bg=COLORS['bg_panel'], padx=12, pady=10)
        panel_frame.pack(fill='both', padx=1, pady=1)

        # Header
        header = tk.Label(
            panel_frame,
            text="SAVED POSITIONS",
            font=FONTS['heading'],
            fg=COLORS['text_accent'],
            bg=COLORS['bg_panel']
        )
        header.pack(anchor='w')

        # Content row
        content_row = tk.Frame(panel_frame, bg=COLORS['bg_panel'])
        content_row.pack(fill='x', pady=(8, 0))

        # Home section
        home_label = tk.Label(
            content_row,
            text="Home:",
            font=FONTS['subheading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel']
        )
        home_label.pack(side='left')

        self._home_pos_var = tk.StringVar(value="Not Set")
        self._home_pos_label = tk.Label(
            content_row,
            textvariable=self._home_pos_var,
            font=FONTS['mono'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel'],
            width=12,
            anchor='w'
        )
        self._home_pos_label.pack(side='left', padx=(4, 0))

        self._save_home_btn = ModernButton(
            content_row,
            text="SAVE",
            command=self._on_save_home,
            width=55,
            height=26,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._save_home_btn.pack(side='left', padx=(8, 0))

        # Spacer
        tk.Frame(content_row, bg=COLORS['bg_panel'], width=24).pack(side='left')

        # Well section
        well_label = tk.Label(
            content_row,
            text="Well:",
            font=FONTS['subheading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel']
        )
        well_label.pack(side='left')

        self._well_pos_var = tk.StringVar(value="Not Set")
        self._well_pos_label = tk.Label(
            content_row,
            textvariable=self._well_pos_var,
            font=FONTS['mono'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel'],
            width=12,
            anchor='w'
        )
        self._well_pos_label.pack(side='left', padx=(4, 0))

        self._save_well_btn = ModernButton(
            content_row,
            text="SAVE",
            command=self._on_save_well,
            width=55,
            height=26,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._save_well_btn.pack(side='left', padx=(8, 0))

        # Spacer
        tk.Frame(content_row, bg=COLORS['bg_panel'], width=24).pack(side='left')

        # Zero button
        self._zero_btn = ModernButton(
            content_row,
            text="ZERO",
            command=self._on_zero_position,
            width=55,
            height=26,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        self._zero_btn.pack(side='left')

        # Spacer
        tk.Frame(content_row, bg=COLORS['bg_panel'], width=12).pack(side='left')

        # Clear Fault button
        self._clear_fault_btn = ModernButton(
            content_row,
            text="CLR FAULT",
            command=self._on_clear_fault if self._on_clear_fault else lambda: None,
            width=75,
            height=26,
            bg_color=COLORS['btn_danger'],
            font=FONTS['small']
        )
        self._clear_fault_btn.pack(side='left')

    def update_home_position(self, saved: bool, position: Optional[int]) -> None:
        """Update home position display."""
        if saved and position is not None:
            self._home_pos_var.set(f"{position:,} steps")
            self._home_pos_label.configure(fg=COLORS['text_primary'])
        else:
            self._home_pos_var.set("Not Set")
            self._home_pos_label.configure(fg=COLORS['text_muted'])

    def update_well_position(self, saved: bool, position: Optional[int]) -> None:
        """Update well position display."""
        if saved and position is not None:
            self._well_pos_var.set(f"{position:,} steps")
            self._well_pos_label.configure(fg=COLORS['text_primary'])
        else:
            self._well_pos_var.set("Not Set")
            self._well_pos_label.configure(fg=COLORS['text_muted'])

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all controls."""
        self._save_home_btn.set_enabled(enabled)
        self._save_well_btn.set_enabled(enabled)
        self._zero_btn.set_enabled(enabled)
        self._clear_fault_btn.set_enabled(enabled)
