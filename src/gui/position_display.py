"""
Position Display Panel

Shows current position, speed, and motion mode with prominent display.
Modern dark theme with LED-style indicators.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..command_protocol import WinchStatus, MotionMode
from .theme import COLORS, FONTS
from .widgets import LEDIndicator


# Color scheme for motion modes
MODE_COLORS = {
    MotionMode.IDLE: COLORS['status_idle'],
    MotionMode.JOG: COLORS['status_jog'],
    MotionMode.MOVE: COLORS['status_move'],
    MotionMode.UNKNOWN: COLORS['status_disabled']
}


class PositionSlider(tk.Frame):
    """
    Visual slider showing position between HOME and WELL.

    Features:
    - Gradient track from HOME to WELL
    - Glowing position indicator
    """

    TRACK_HEIGHT = 16
    INDICATOR_SIZE = 28
    DEST_TOLERANCE = 100  # Steps tolerance for "at destination"

    def __init__(self, parent, height=70, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], **kwargs)

        self._height = height
        self._home_pos = None
        self._well_pos = None
        self._current_pos = None
        self._last_fraction = 0.5
        self._at_destination = False
        self._destination_name = None

        # Create border frame
        self._border = tk.Frame(self, bg=COLORS['border'], padx=1, pady=1)
        self._border.pack(fill='x', padx=8, pady=4)

        # Create inner panel
        self._panel = tk.Frame(self._border, bg=COLORS['bg_panel'])
        self._panel.pack(fill='x')

        # Create canvas for slider
        self._canvas = tk.Canvas(
            self._panel, height=height,
            bg=COLORS['bg_panel'], highlightthickness=0
        )
        self._canvas.pack(fill='x', padx=8, pady=8)

        # Bind resize event
        self._canvas.bind('<Configure>', self._on_resize)

        # Track geometry (will be updated on resize)
        self._track_left = 80
        self._track_right = 200
        self._track_width = self._track_right - self._track_left
        self._track_y = height // 2

    def _on_resize(self, event):
        """Handle canvas resize."""
        width = event.width
        if width > 100:
            self._track_left = 80
            self._track_right = width - 80
            self._track_width = self._track_right - self._track_left
            self._redraw()

    def _redraw(self):
        """Redraw everything."""
        self._canvas.delete('all')
        self._draw_static()
        self._draw_indicator(self._last_fraction)

    def _draw_static(self):
        """Draw static elements (track, labels)."""
        c = self._canvas

        # Track background (dark recessed look)
        c.create_rectangle(
            self._track_left - 2, self._track_y - self.TRACK_HEIGHT//2 - 2,
            self._track_right + 2, self._track_y + self.TRACK_HEIGHT//2 + 2,
            fill=COLORS['bg_dark'], outline=COLORS['border'], width=1
        )

        # Track gradient (blue to cyan)
        steps = 30
        for i in range(steps):
            x1 = self._track_left + (self._track_width * i // steps)
            x2 = self._track_left + (self._track_width * (i + 1) // steps)
            # Interpolate color from dark blue to cyan
            r = int(30 + (0 - 30) * i / steps)
            g = int(60 + (180 - 60) * i / steps)
            b = int(120 + (220 - 120) * i / steps)
            color = f'#{r:02x}{g:02x}{b:02x}'
            c.create_rectangle(
                x1, self._track_y - self.TRACK_HEIGHT//2,
                x2, self._track_y + self.TRACK_HEIGHT//2,
                fill=color, outline=''
            )

        # HOME label (left)
        c.create_text(
            self._track_left - 10, self._track_y,
            text="HOME", font=FONTS['heading'], fill=COLORS['accent_green'],
            anchor='e'
        )

        # WELL label (right)
        c.create_text(
            self._track_right + 10, self._track_y,
            text="WELL", font=FONTS['heading'], fill=COLORS['accent_cyan'],
            anchor='w'
        )

        # Home marker
        c.create_line(
            self._track_left, self._track_y - self.TRACK_HEIGHT//2 - 6,
            self._track_left, self._track_y + self.TRACK_HEIGHT//2 + 6,
            fill=COLORS['accent_green'], width=3
        )

        # Well marker
        c.create_line(
            self._track_right, self._track_y - self.TRACK_HEIGHT//2 - 6,
            self._track_right, self._track_y + self.TRACK_HEIGHT//2 + 6,
            fill=COLORS['accent_cyan'], width=3
        )

    def _draw_indicator(self, fraction: float):
        """Draw the position indicator at given fraction (0=home, 1=well)."""
        c = self._canvas

        # Delete old indicator elements
        c.delete('indicator')
        c.delete('glow')

        # Store for redraw
        self._last_fraction = fraction

        # Clamp fraction
        fraction = max(0.0, min(1.0, fraction))

        # Calculate x position
        x = self._track_left + (self._track_width * fraction)
        y = self._track_y

        # Determine indicator color based on position and movement
        if self._at_destination:
            indicator_color = '#00ff00'
            glow_color = '#00ff00'
        else:
            # Gradient from green (home) to cyan (well)
            r = int(0 + (0 - 0) * fraction)
            g = int(255 + (200 - 255) * fraction)
            b = int(100 + (255 - 100) * fraction)
            indicator_color = f'#{r:02x}{g:02x}{b:02x}'
            glow_color = indicator_color

        # Draw glow effect (multiple rings for glow look)
        for i in range(4, 0, -1):
            size = self.INDICATOR_SIZE//2 + i * 4
            c.create_oval(
                x - size, y - size,
                x + size, y + size,
                fill='', outline=glow_color, width=2,
                tags='glow'
            )

        # Draw main indicator (filled circle)
        size = self.INDICATOR_SIZE // 2
        c.create_oval(
            x - size, y - size,
            x + size, y + size,
            fill=indicator_color, outline='#ffffff', width=2,
            tags='indicator'
        )

        # Draw inner highlight
        inner_size = size - 5
        c.create_oval(
            x - inner_size, y - inner_size,
            x + inner_size//2, y - 2,
            fill='#ffffff', outline='',
            tags='indicator'
        )

    def update_position(self, current: int, home: Optional[int], well: Optional[int]):
        """Update the slider with new position data."""
        self._current_pos = current
        self._home_pos = home
        self._well_pos = well

        # Check if at destination
        self._at_destination = False
        self._destination_name = None

        if home is not None and abs(current - home) <= self.DEST_TOLERANCE:
            self._at_destination = True
            self._destination_name = "HOME"
        elif well is not None and abs(current - well) <= self.DEST_TOLERANCE:
            self._at_destination = True
            self._destination_name = "WELL"

        # Calculate fraction (0 = home, 1 = well)
        if home is not None and well is not None and home != well:
            fraction = (current - home) / (well - home)
        elif home is not None:
            fraction = 0.0
        elif well is not None:
            fraction = 1.0
        else:
            fraction = 0.5

        self._draw_indicator(fraction)

    def set_disconnected(self):
        """Show disconnected state."""
        self._home_pos = None
        self._well_pos = None
        self._current_pos = None
        self._at_destination = False
        self._destination_name = None
        self._draw_indicator(0.5)


class PositionDisplay(tk.Frame):
    """
    Widget displaying current position, speed, and motion mode.

    Features:
    - Large digital position display with glow effect
    - Position converted to revolutions
    - Current speed in RPS with styled display
    - LED-style color-coded motion mode indicator
    """

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, bg=COLORS['bg_dark'])
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create and layout display widgets."""
        # Configure frame
        self.columnconfigure(0, weight=1)

        # Main panel with border
        panel_border = tk.Frame(self, bg=COLORS['border'])
        panel_border.grid(row=0, column=0, sticky="ew", padx=8, pady=4)

        main_frame = tk.Frame(panel_border, bg=COLORS['bg_panel'], padx=12, pady=10)
        main_frame.pack(fill='both', padx=1, pady=1)

        # Header
        header = tk.Label(
            main_frame,
            text="STATUS",
            font=FONTS['heading'],
            fg=COLORS['text_accent'],
            bg=COLORS['bg_panel']
        )
        header.pack(anchor='w')

        # Content row
        content_frame = tk.Frame(main_frame, bg=COLORS['bg_panel'])
        content_frame.pack(fill='x', pady=(8, 0))

        # === Position Display (left side) ===
        pos_container = tk.Frame(content_frame, bg=COLORS['bg_panel'])
        pos_container.pack(side='left', fill='y')

        # Position display with dark recessed background
        pos_display_border = tk.Frame(pos_container, bg=COLORS['border'])
        pos_display_border.pack(side='left')

        pos_display = tk.Frame(pos_display_border, bg=COLORS['bg_display'], padx=16, pady=8)
        pos_display.pack(padx=1, pady=1)

        self._position_var = tk.StringVar(value="---")
        self._position_label = tk.Label(
            pos_display,
            textvariable=self._position_var,
            font=FONTS['display_large'],
            bg=COLORS['bg_display'],
            fg=COLORS['accent_green']
        )
        self._position_label.pack(side='left')

        # Units column
        unit_frame = tk.Frame(pos_container, bg=COLORS['bg_panel'])
        unit_frame.pack(side='left', padx=(10, 0), fill='y', expand=False)

        steps_label = tk.Label(
            unit_frame,
            text="steps",
            font=FONTS['small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        steps_label.pack(anchor='w', pady=(8, 0))

        self._revolutions_var = tk.StringVar(value="---")
        rev_label = tk.Label(
            unit_frame,
            textvariable=self._revolutions_var,
            font=FONTS['display_small'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        )
        rev_label.pack(anchor='w')

        rev_unit = tk.Label(
            unit_frame,
            text="rev",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        rev_unit.pack(anchor='w')

        # === Speed Display (middle) ===
        speed_container = tk.Frame(content_frame, bg=COLORS['bg_panel'])
        speed_container.pack(side='left', padx=(30, 0), fill='y')

        speed_title = tk.Label(
            speed_container,
            text="SPEED",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        speed_title.pack()

        # Speed value with styled background
        speed_display_border = tk.Frame(speed_container, bg=COLORS['border'])
        speed_display_border.pack(pady=(4, 0))

        speed_display = tk.Frame(speed_display_border, bg=COLORS['bg_display'], padx=12, pady=4)
        speed_display.pack(padx=1, pady=1)

        self._speed_var = tk.StringVar(value="0.00")
        speed_value = tk.Label(
            speed_display,
            textvariable=self._speed_var,
            font=FONTS['display_medium'],
            fg=COLORS['accent_cyan'],
            bg=COLORS['bg_display']
        )
        speed_value.pack()

        speed_unit = tk.Label(
            speed_container,
            text="RPS",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        speed_unit.pack()

        # === Mode Display (right side) ===
        mode_container = tk.Frame(content_frame, bg=COLORS['bg_panel'])
        mode_container.pack(side='left', padx=(30, 0), fill='y')

        mode_title = tk.Label(
            mode_container,
            text="MODE",
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        mode_title.pack()

        # Mode indicator with LED
        mode_row = tk.Frame(mode_container, bg=COLORS['bg_panel'])
        mode_row.pack(pady=(4, 0))

        self._mode_led = LEDIndicator(mode_row, size=12, bg=COLORS['bg_panel'])
        self._mode_led.pack(side='left', padx=(0, 8))

        self._mode_var = tk.StringVar(value="---")
        self._mode_label = tk.Label(
            mode_row,
            textvariable=self._mode_var,
            font=FONTS['subheading'],
            width=8,
            anchor='w',
            bg=COLORS['bg_panel'],
            fg=COLORS['status_disabled']
        )
        self._mode_label.pack(side='left')

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
            self._mode_led.set_state('disabled')
            self._mode_label.configure(fg=COLORS['status_disabled'])
            self._position_label.configure(fg=COLORS['text_muted'])
            return

        # Update position
        self._position_var.set(f"{status.position:,}")
        self._revolutions_var.set(f"{status.position_revolutions:.3f}")

        # Update speed
        self._speed_var.set(f"{status.speed_rps:.2f}")

        # Update mode with color
        self._mode_var.set(status.mode.value)
        mode_color = MODE_COLORS.get(status.mode, MODE_COLORS[MotionMode.UNKNOWN])
        self._mode_label.configure(fg=mode_color)

        # Update LED based on mode
        if status.mode == MotionMode.IDLE:
            self._mode_led.set_state('idle')
        elif status.mode == MotionMode.JOG:
            self._mode_led.set_state('jog')
        elif status.mode == MotionMode.MOVE:
            self._mode_led.set_state('move')
        else:
            self._mode_led.set_state('disabled')

        # Position color based on mode
        if status.mode == MotionMode.IDLE:
            self._position_label.configure(fg=COLORS['accent_green'])
        elif status.mode == MotionMode.JOG:
            self._position_label.configure(fg=COLORS['status_jog'])
        else:
            self._position_label.configure(fg=COLORS['accent_cyan'])

    def set_disconnected(self) -> None:
        """Show disconnected state."""
        self.update_status(None)
