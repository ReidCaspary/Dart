"""
Settings Dialog

Allows adjusting speed settings for jog and move operations.
Modern dark theme styling.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import COLORS, FONTS
from .widgets import ModernButton, ModernScale


class SettingsDialog(tk.Toplevel):
    """
    Modal dialog for adjusting winch speed settings.
    """

    def __init__(
        self,
        parent: tk.Widget,
        current_jog_rps: float,
        current_move_rps: float,
        on_apply: Callable[[float, float], None]
    ):
        super().__init__(parent)

        self._on_apply = on_apply
        self._current_jog = current_jog_rps
        self._current_move = current_move_rps

        self.title("Speed Settings")
        self.configure(bg=COLORS['bg_dark'])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Border frame
        border = tk.Frame(self, bg=COLORS['border'])
        border.pack(fill='both', expand=True, padx=1, pady=1)

        main_frame = tk.Frame(border, bg=COLORS['bg_panel'], padx=20, pady=15)
        main_frame.pack(fill='both', expand=True)

        # Header
        header = tk.Label(
            main_frame,
            text="Speed Settings",
            font=FONTS['heading'],
            fg=COLORS['text_accent'],
            bg=COLORS['bg_panel']
        )
        header.grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 4))

        # Info label
        info_label = tk.Label(
            main_frame,
            text="Lower speeds = more torque. Adjust if motor is stalling.",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        info_label.grid(row=1, column=0, columnspan=3, sticky='w', pady=(0, 16))

        # Jog Speed
        jog_label = tk.Label(
            main_frame,
            text="Jog Speed:",
            font=FONTS['subheading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel']
        )
        jog_label.grid(row=2, column=0, sticky='w', pady=8)

        self._jog_var = tk.DoubleVar(value=self._current_jog)
        self._jog_scale = ModernScale(
            main_frame,
            from_=0.5,
            to=15.0,
            value=self._current_jog,
            command=self._on_jog_change,
            width=180,
            height=24,
            bg=COLORS['bg_panel']
        )
        self._jog_scale.grid(row=2, column=1, padx=12, pady=8)

        self._jog_label = tk.Label(
            main_frame,
            text=f"{self._current_jog:.1f} RPS",
            font=FONTS['mono'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel'],
            width=8
        )
        self._jog_label.grid(row=2, column=2, pady=8)

        # Move Speed
        move_label = tk.Label(
            main_frame,
            text="Move Speed:",
            font=FONTS['subheading'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel']
        )
        move_label.grid(row=3, column=0, sticky='w', pady=8)

        self._move_var = tk.DoubleVar(value=self._current_move)
        self._move_scale = ModernScale(
            main_frame,
            from_=0.5,
            to=15.0,
            value=self._current_move,
            command=self._on_move_change,
            width=180,
            height=24,
            bg=COLORS['bg_panel']
        )
        self._move_scale.grid(row=3, column=1, padx=12, pady=8)

        self._move_label = tk.Label(
            main_frame,
            text=f"{self._current_move:.1f} RPS",
            font=FONTS['mono'],
            fg=COLORS['text_primary'],
            bg=COLORS['bg_panel'],
            width=8
        )
        self._move_label.grid(row=3, column=2, pady=8)

        # Preset buttons section
        preset_border = tk.Frame(main_frame, bg=COLORS['border'])
        preset_border.grid(row=4, column=0, columnspan=3, sticky='ew', pady=(16, 0))

        preset_frame = tk.Frame(preset_border, bg=COLORS['bg_header'], padx=12, pady=10)
        preset_frame.pack(fill='x', padx=1, pady=1)

        preset_label = tk.Label(
            preset_frame,
            text="Presets:",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_header']
        )
        preset_label.pack(side='left')

        slow_btn = ModernButton(
            preset_frame,
            text="Slow (2 RPS)",
            command=lambda: self._set_preset(2.0, 1.5),
            width=100,
            height=28,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        slow_btn.pack(side='left', padx=(12, 4))

        medium_btn = ModernButton(
            preset_frame,
            text="Medium (5 RPS)",
            command=lambda: self._set_preset(5.0, 4.0),
            width=110,
            height=28,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        medium_btn.pack(side='left', padx=4)

        fast_btn = ModernButton(
            preset_frame,
            text="Fast (10 RPS)",
            command=lambda: self._set_preset(10.0, 7.5),
            width=100,
            height=28,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['small']
        )
        fast_btn.pack(side='left', padx=4)

        # Action buttons
        btn_frame = tk.Frame(main_frame, bg=COLORS['bg_panel'])
        btn_frame.grid(row=5, column=0, columnspan=3, pady=(20, 0))

        apply_btn = ModernButton(
            btn_frame,
            text="Apply",
            command=self._apply,
            width=90,
            height=32,
            bg_color=COLORS['btn_primary'],
            font=FONTS['button']
        )
        apply_btn.pack(side='left', padx=(0, 8))

        cancel_btn = ModernButton(
            btn_frame,
            text="Cancel",
            command=self.destroy,
            width=90,
            height=32,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['button']
        )
        cancel_btn.pack(side='left')

    def _on_jog_change(self, value: float) -> None:
        """Handle jog slider change."""
        self._jog_var.set(value)
        self._jog_label.config(text=f"{value:.1f} RPS")

    def _on_move_change(self, value: float) -> None:
        """Handle move slider change."""
        self._move_var.set(value)
        self._move_label.config(text=f"{value:.1f} RPS")

    def _set_preset(self, jog: float, move: float) -> None:
        """Set a speed preset."""
        self._jog_var.set(jog)
        self._move_var.set(move)
        self._jog_scale.set(jog)
        self._move_scale.set(move)
        self._jog_label.config(text=f"{jog:.1f} RPS")
        self._move_label.config(text=f"{move:.1f} RPS")

    def _apply(self) -> None:
        """Apply settings and close."""
        jog_rps = self._jog_var.get()
        move_rps = self._move_var.get()
        self._on_apply(jog_rps, move_rps)
        self.destroy()
