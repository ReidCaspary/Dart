"""
Settings Dialog

Allows adjusting speed settings for jog and move operations.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


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
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Info label
        info_label = ttk.Label(
            main_frame,
            text="Lower speeds = more torque\nAdjust if motor is stalling",
            font=("Arial", 9),
            foreground="gray"
        )
        info_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # Jog Speed
        ttk.Label(main_frame, text="Jog Speed:", font=("Arial", 10, "bold")).grid(
            row=1, column=0, sticky="w", pady=5
        )

        self._jog_var = tk.DoubleVar(value=self._current_jog)
        self._jog_scale = ttk.Scale(
            main_frame,
            from_=0.5,
            to=15.0,
            variable=self._jog_var,
            orient=tk.HORIZONTAL,
            length=200,
            command=self._on_jog_change
        )
        self._jog_scale.grid(row=1, column=1, padx=10, pady=5)

        self._jog_label = ttk.Label(main_frame, text=f"{self._current_jog:.1f} RPS", width=8)
        self._jog_label.grid(row=1, column=2, pady=5)

        # Move Speed
        ttk.Label(main_frame, text="Move Speed:", font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky="w", pady=5
        )

        self._move_var = tk.DoubleVar(value=self._current_move)
        self._move_scale = ttk.Scale(
            main_frame,
            from_=0.5,
            to=15.0,
            variable=self._move_var,
            orient=tk.HORIZONTAL,
            length=200,
            command=self._on_move_change
        )
        self._move_scale.grid(row=2, column=1, padx=10, pady=5)

        self._move_label = ttk.Label(main_frame, text=f"{self._current_move:.1f} RPS", width=8)
        self._move_label.grid(row=2, column=2, pady=5)

        # Preset buttons
        preset_frame = ttk.LabelFrame(main_frame, text="Presets", padding=5)
        preset_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Button(preset_frame, text="Slow (2 RPS)", command=lambda: self._set_preset(2.0, 1.5), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Medium (5 RPS)", command=lambda: self._set_preset(5.0, 4.0), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Fast (10 RPS)", command=lambda: self._set_preset(10.0, 7.5), width=12).pack(side=tk.LEFT, padx=2)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))

        ttk.Button(btn_frame, text="Apply", command=self._apply, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side=tk.LEFT, padx=5)

    def _on_jog_change(self, value: str) -> None:
        """Handle jog slider change."""
        val = float(value)
        self._jog_label.config(text=f"{val:.1f} RPS")

    def _on_move_change(self, value: str) -> None:
        """Handle move slider change."""
        val = float(value)
        self._move_label.config(text=f"{val:.1f} RPS")

    def _set_preset(self, jog: float, move: float) -> None:
        """Set a speed preset."""
        self._jog_var.set(jog)
        self._move_var.set(move)
        self._jog_label.config(text=f"{jog:.1f} RPS")
        self._move_label.config(text=f"{move:.1f} RPS")

    def _apply(self) -> None:
        """Apply settings and close."""
        jog_rps = self._jog_var.get()
        move_rps = self._move_var.get()
        self._on_apply(jog_rps, move_rps)
        self.destroy()
