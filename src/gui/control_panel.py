"""
Control Panel

Contains jog buttons, go-to controls, and stop button.
Modern dark theme with styled buttons.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import COLORS, FONTS
from .widgets import HoldButton, ModernButton, ModernEntry


class ControlPanel(tk.Frame):
    """
    Main control panel with jog buttons and motion controls.

    Features:
    - Press-and-hold jog buttons (JL/JR on press, JS on release)
    - Go Home / Go Well buttons
    - Absolute and relative position move inputs
    - Emergency stop button
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_jog_left_press: Callable[[], None],
        on_jog_left_release: Callable[[], None],
        on_jog_right_press: Callable[[], None],
        on_jog_right_release: Callable[[], None],
        on_go_home: Callable[[], None],
        on_go_well: Callable[[], None],
        on_stop: Callable[[], None],
        on_go_to: Callable[[int], None],
        on_move_relative: Callable[[int], None]
    ):
        super().__init__(parent, bg=COLORS['bg_dark'])

        # Store callbacks
        self._on_jog_left_press = on_jog_left_press
        self._on_jog_left_release = on_jog_left_release
        self._on_jog_right_press = on_jog_right_press
        self._on_jog_right_release = on_jog_right_release
        self._on_go_home = on_go_home
        self._on_go_well = on_go_well
        self._on_stop = on_stop
        self._on_go_to = on_go_to
        self._on_move_relative = on_move_relative

        # Track button states
        self._jog_left_active = False
        self._jog_right_active = False

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout control widgets."""
        self.columnconfigure(0, weight=1)

        # === Jog Control Section ===
        jog_border = tk.Frame(self, bg=COLORS['border'])
        jog_border.grid(row=0, column=0, sticky="ew", padx=8, pady=4)

        jog_frame = tk.Frame(jog_border, bg=COLORS['bg_panel'], padx=12, pady=10)
        jog_frame.pack(fill='both', padx=1, pady=1)

        # Header
        jog_header = tk.Label(
            jog_frame,
            text="JOG CONTROL",
            font=FONTS['heading'],
            fg=COLORS['text_accent'],
            bg=COLORS['bg_panel']
        )
        jog_header.pack(anchor='w')

        jog_hint = tk.Label(
            jog_frame,
            text="Hold button or use arrow keys",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        jog_hint.pack(anchor='w')

        # Jog buttons row
        jog_buttons = tk.Frame(jog_frame, bg=COLORS['bg_panel'])
        jog_buttons.pack(fill='x', pady=(10, 0))
        jog_buttons.columnconfigure(0, weight=1)
        jog_buttons.columnconfigure(1, weight=1)

        # Jog Left Button
        self._jog_left_btn = HoldButton(
            jog_buttons,
            text="\u25C4 WELL",
            on_press=self._on_jog_left_press,
            on_release=self._on_jog_left_release,
            width=180,
            height=48,
            bg_color=COLORS['btn_jog'],
            hover_color=COLORS['btn_jog_hover'],
            press_color=COLORS['btn_jog_press'],
            font=FONTS['button_large'],
            glow=True,
            glow_color=COLORS['glow_blue']
        )
        self._jog_left_btn.grid(row=0, column=0, sticky='ew', padx=(0, 6))

        # Jog Right Button
        self._jog_right_btn = HoldButton(
            jog_buttons,
            text="HOME \u25BA",
            on_press=self._on_jog_right_press,
            on_release=self._on_jog_right_release,
            width=180,
            height=48,
            bg_color=COLORS['btn_jog'],
            hover_color=COLORS['btn_jog_hover'],
            press_color=COLORS['btn_jog_press'],
            font=FONTS['button_large'],
            glow=True,
            glow_color=COLORS['glow_blue']
        )
        self._jog_right_btn.grid(row=0, column=1, sticky='ew', padx=(6, 0))

        # === Position Control Section ===
        pos_border = tk.Frame(self, bg=COLORS['border'])
        pos_border.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

        pos_frame = tk.Frame(pos_border, bg=COLORS['bg_panel'], padx=12, pady=10)
        pos_frame.pack(fill='both', padx=1, pady=1)

        # Header
        pos_header = tk.Label(
            pos_frame,
            text="POSITION CONTROL",
            font=FONTS['heading'],
            fg=COLORS['text_accent'],
            bg=COLORS['bg_panel']
        )
        pos_header.pack(anchor='w')

        # Button row: GO HOME, GO WELL, STOP
        btn_row = tk.Frame(pos_frame, bg=COLORS['bg_panel'])
        btn_row.pack(fill='x', pady=(10, 0))

        self._go_home_btn = ModernButton(
            btn_row,
            text="GO HOME",
            command=self._on_go_home,
            width=100,
            height=36,
            bg_color=COLORS['btn_primary'],
            font=FONTS['button']
        )
        self._go_home_btn.pack(side='left', padx=(0, 8))

        self._go_well_btn = ModernButton(
            btn_row,
            text="GO WELL",
            command=self._on_go_well,
            width=100,
            height=36,
            bg_color=COLORS['btn_primary'],
            font=FONTS['button']
        )
        self._go_well_btn.pack(side='left', padx=(0, 8))

        # Spacer
        spacer = tk.Frame(btn_row, bg=COLORS['bg_panel'])
        spacer.pack(side='left', fill='x', expand=True)

        # STOP button
        self._stop_btn = ModernButton(
            btn_row,
            text="STOP",
            command=self._on_stop,
            width=100,
            height=36,
            bg_color=COLORS['btn_danger'],
            hover_color=COLORS['btn_danger_hover'],
            font=FONTS['button'],
            glow=True,
            glow_color=COLORS['glow_red']
        )
        self._stop_btn.pack(side='right')

        # Input row: Go To
        goto_row = tk.Frame(pos_frame, bg=COLORS['bg_panel'])
        goto_row.pack(fill='x', pady=(12, 0))

        goto_label = tk.Label(
            goto_row,
            text="Go To:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel'],
            width=8,
            anchor='e'
        )
        goto_label.pack(side='left')

        self._goto_entry = ModernEntry(goto_row, width=14)
        self._goto_entry.pack(side='left', padx=(8, 0))
        self._goto_entry.bind("<Return>", lambda e: self._execute_goto())

        self._goto_btn = ModernButton(
            goto_row,
            text="GO",
            command=self._execute_goto,
            width=60,
            height=30,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['body']
        )
        self._goto_btn.pack(side='left', padx=(8, 0))

        # Input row: Move Relative
        rel_row = tk.Frame(pos_frame, bg=COLORS['bg_panel'])
        rel_row.pack(fill='x', pady=(8, 0))

        rel_label = tk.Label(
            rel_row,
            text="Move Rel:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel'],
            width=8,
            anchor='e'
        )
        rel_label.pack(side='left')

        self._rel_entry = ModernEntry(rel_row, width=14)
        self._rel_entry.pack(side='left', padx=(8, 0))
        self._rel_entry.bind("<Return>", lambda e: self._execute_relative())

        self._rel_btn = ModernButton(
            rel_row,
            text="MOVE",
            command=self._execute_relative,
            width=60,
            height=30,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['body']
        )
        self._rel_btn.pack(side='left', padx=(8, 0))

    def _execute_goto(self) -> None:
        """Execute go-to command from entry field."""
        try:
            value = self._goto_entry.get().strip().replace(",", "")
            if value:
                steps = int(value)
                self._on_go_to(steps)
                self._goto_entry.delete(0, tk.END)
        except ValueError:
            pass  # Invalid input, ignore

    def _execute_relative(self) -> None:
        """Execute relative move command from entry field."""
        try:
            value = self._rel_entry.get().strip().replace(",", "")
            if value:
                steps = int(value)
                self._on_move_relative(steps)
                self._rel_entry.delete(0, tk.END)
        except ValueError:
            pass  # Invalid input, ignore

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all controls."""
        self._jog_left_btn.set_enabled(enabled)
        self._jog_right_btn.set_enabled(enabled)
        self._go_home_btn.set_enabled(enabled)
        self._go_well_btn.set_enabled(enabled)
        self._stop_btn.set_enabled(enabled)
        self._goto_btn.set_enabled(enabled)
        self._rel_btn.set_enabled(enabled)
        self._goto_entry.set_enabled(enabled)
        self._rel_entry.set_enabled(enabled)

    def set_home_enabled(self, enabled: bool) -> None:
        """Enable or disable Go Home button based on home saved state."""
        self._go_home_btn.set_enabled(enabled)

    def set_well_enabled(self, enabled: bool) -> None:
        """Enable or disable Go Well button based on well saved state."""
        self._go_well_btn.set_enabled(enabled)

    def trigger_jog_left(self, pressed: bool) -> None:
        """Trigger jog left from keyboard."""
        if pressed:
            self._jog_left_btn.trigger_press()
        else:
            self._jog_left_btn.trigger_release()

    def trigger_jog_right(self, pressed: bool) -> None:
        """Trigger jog right from keyboard."""
        if pressed:
            self._jog_right_btn.trigger_press()
        else:
            self._jog_right_btn.trigger_release()
