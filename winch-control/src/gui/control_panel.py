"""
Control Panel

Contains jog buttons, go-to controls, and stop button.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class ControlPanel(ttk.Frame):
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
        super().__init__(parent)

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

        # Jog Control Section
        jog_frame = ttk.LabelFrame(self, text="Jog (hold button or arrow keys)", padding=5)
        jog_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        jog_frame.columnconfigure(0, weight=1)
        jog_frame.columnconfigure(1, weight=1)

        # Jog Left Button
        self._jog_left_btn = tk.Button(
            jog_frame,
            text="\u25C4 WELL",
            font=("Arial", 11, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#1976D2",
            activeforeground="white",
            relief=tk.RAISED,
            cursor="hand2"
        )
        self._jog_left_btn.grid(row=0, column=0, sticky="ew", padx=(0, 2), ipady=5)

        self._jog_left_btn.bind("<ButtonPress-1>", self._on_jog_left_button_press)
        self._jog_left_btn.bind("<ButtonRelease-1>", self._on_jog_left_button_release)

        # Jog Right Button
        self._jog_right_btn = tk.Button(
            jog_frame,
            text="HOME \u25BA",
            font=("Arial", 11, "bold"),
            bg="#2196F3",
            fg="white",
            activebackground="#1976D2",
            activeforeground="white",
            relief=tk.RAISED,
            cursor="hand2"
        )
        self._jog_right_btn.grid(row=0, column=1, sticky="ew", padx=(2, 0), ipady=5)

        self._jog_right_btn.bind("<ButtonPress-1>", self._on_jog_right_button_press)
        self._jog_right_btn.bind("<ButtonRelease-1>", self._on_jog_right_button_release)

        # Position Control Section - more compact
        pos_frame = ttk.LabelFrame(self, text="Position Control", padding=5)
        pos_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        pos_frame.columnconfigure(1, weight=1)

        # Row 0: GO HOME, GO WELL, STOP
        self._go_home_btn = ttk.Button(pos_frame, text="GO HOME", command=self._on_go_home, width=10)
        self._go_home_btn.grid(row=0, column=0, padx=2, pady=2)

        self._go_well_btn = ttk.Button(pos_frame, text="GO WELL", command=self._on_go_well, width=10)
        self._go_well_btn.grid(row=0, column=1, padx=2, pady=2, sticky="w")

        self._stop_btn = tk.Button(
            pos_frame, text="STOP", font=("Arial", 11, "bold"),
            bg="#D32F2F", fg="white", activebackground="#B71C1C",
            activeforeground="white", cursor="hand2", command=self._on_stop, width=10
        )
        self._stop_btn.grid(row=0, column=2, padx=2, pady=2, sticky="e")

        # Row 1: Go To
        ttk.Label(pos_frame, text="Go To:").grid(row=1, column=0, sticky="e", padx=2, pady=2)
        goto_frame = ttk.Frame(pos_frame)
        goto_frame.grid(row=1, column=1, columnspan=2, sticky="ew", padx=2, pady=2)
        goto_frame.columnconfigure(0, weight=1)

        self._goto_entry = ttk.Entry(goto_frame, width=12)
        self._goto_entry.grid(row=0, column=0, sticky="ew")
        self._goto_entry.bind("<Return>", lambda e: self._execute_goto())

        self._goto_btn = ttk.Button(goto_frame, text="GO", command=self._execute_goto, width=5)
        self._goto_btn.grid(row=0, column=1, padx=(3, 0))

        # Row 2: Move Relative
        ttk.Label(pos_frame, text="Move Rel:").grid(row=2, column=0, sticky="e", padx=2, pady=2)
        rel_frame = ttk.Frame(pos_frame)
        rel_frame.grid(row=2, column=1, columnspan=2, sticky="ew", padx=2, pady=2)
        rel_frame.columnconfigure(0, weight=1)

        self._rel_entry = ttk.Entry(rel_frame, width=12)
        self._rel_entry.grid(row=0, column=0, sticky="ew")
        self._rel_entry.bind("<Return>", lambda e: self._execute_relative())

        self._rel_btn = ttk.Button(rel_frame, text="MOVE", command=self._execute_relative, width=5)
        self._rel_btn.grid(row=0, column=1, padx=(3, 0))

    def _on_jog_left_button_press(self, event: tk.Event) -> None:
        """Handle jog left button press."""
        if not self._jog_left_active:
            self._jog_left_active = True
            self._jog_left_btn.configure(relief=tk.SUNKEN, bg="#1565C0")
            self._on_jog_left_press()

    def _on_jog_left_button_release(self, event: tk.Event) -> None:
        """Handle jog left button release."""
        if self._jog_left_active:
            self._jog_left_active = False
            self._jog_left_btn.configure(relief=tk.RAISED, bg="#2196F3")
            self._on_jog_left_release()

    def _on_jog_right_button_press(self, event: tk.Event) -> None:
        """Handle jog right button press."""
        if not self._jog_right_active:
            self._jog_right_active = True
            self._jog_right_btn.configure(relief=tk.SUNKEN, bg="#1565C0")
            self._on_jog_right_press()

    def _on_jog_right_button_release(self, event: tk.Event) -> None:
        """Handle jog right button release."""
        if self._jog_right_active:
            self._jog_right_active = False
            self._jog_right_btn.configure(relief=tk.RAISED, bg="#2196F3")
            self._on_jog_right_release()

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
        state = tk.NORMAL if enabled else tk.DISABLED

        self._jog_left_btn.configure(state=state)
        self._jog_right_btn.configure(state=state)
        self._go_home_btn.configure(state=state)
        self._go_well_btn.configure(state=state)
        self._stop_btn.configure(state=state)
        self._goto_btn.configure(state=state)
        self._rel_btn.configure(state=state)
        self._goto_entry.configure(state=state)
        self._rel_entry.configure(state=state)

        if not enabled:
            # Reset visual states
            self._jog_left_btn.configure(relief=tk.RAISED, bg="#9E9E9E")
            self._jog_right_btn.configure(relief=tk.RAISED, bg="#9E9E9E")
            self._stop_btn.configure(bg="#9E9E9E")
        else:
            self._jog_left_btn.configure(bg="#2196F3")
            self._jog_right_btn.configure(bg="#2196F3")
            self._stop_btn.configure(bg="#D32F2F")

    def set_home_enabled(self, enabled: bool) -> None:
        """Enable or disable Go Home button based on home saved state."""
        self._go_home_btn.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def set_well_enabled(self, enabled: bool) -> None:
        """Enable or disable Go Well button based on well saved state."""
        self._go_well_btn.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def trigger_jog_left(self, pressed: bool) -> None:
        """Trigger jog left from keyboard."""
        if pressed and not self._jog_left_active:
            self._jog_left_active = True
            self._jog_left_btn.configure(relief=tk.SUNKEN, bg="#1565C0")
            self._on_jog_left_press()
        elif not pressed and self._jog_left_active:
            self._jog_left_active = False
            self._jog_left_btn.configure(relief=tk.RAISED, bg="#2196F3")
            self._on_jog_left_release()

    def trigger_jog_right(self, pressed: bool) -> None:
        """Trigger jog right from keyboard."""
        if pressed and not self._jog_right_active:
            self._jog_right_active = True
            self._jog_right_btn.configure(relief=tk.SUNKEN, bg="#1565C0")
            self._on_jog_right_press()
        elif not pressed and self._jog_right_active:
            self._jog_right_active = False
            self._jog_right_btn.configure(relief=tk.RAISED, bg="#2196F3")
            self._on_jog_right_release()
