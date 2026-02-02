"""
Custom Modern Widgets

Canvas-based widgets with hover effects, rounded corners, and glow effects
for the Industrial Neon theme.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import COLORS, FONTS, create_rounded_rect, lighten_color, darken_color


class ModernButton(tk.Canvas):
    """
    Custom button with modern styling:
    - Rounded corners via Canvas
    - Hover color transitions
    - Press depression effect
    - Optional glow effect
    """

    def __init__(
        self,
        parent,
        text: str,
        command: Optional[Callable] = None,
        bg_color: str = None,
        hover_color: str = None,
        press_color: str = None,
        fg_color: str = 'white',
        disabled_bg: str = None,
        disabled_fg: str = None,
        width: int = 100,
        height: int = 36,
        corner_radius: int = 6,
        font: tuple = None,
        glow: bool = False,
        glow_color: str = None
    ):
        # Default colors
        bg_color = bg_color or COLORS['btn_secondary']
        hover_color = hover_color or lighten_color(bg_color, 0.15)
        press_color = press_color or darken_color(bg_color, 0.1)
        disabled_bg = disabled_bg or COLORS['status_disabled']
        disabled_fg = disabled_fg or COLORS['text_muted']
        font = font or FONTS['button']
        glow_color = glow_color or bg_color

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS['bg_panel'],
            highlightthickness=0,
            cursor='hand2'
        )

        self._text = text
        self._command = command
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._press_color = press_color
        self._fg_color = fg_color
        self._disabled_bg = disabled_bg
        self._disabled_fg = disabled_fg
        self._width = width
        self._height = height
        self._corner_radius = corner_radius
        self._font = font
        self._glow = glow
        self._glow_color = glow_color
        self._enabled = True
        self._pressed = False
        self._hovered = False

        self._draw()

        # Bind events
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)

    def _draw(self):
        """Draw the button."""
        self.delete('all')

        # Determine current colors
        if not self._enabled:
            bg = self._disabled_bg
            fg = self._disabled_fg
        elif self._pressed:
            bg = self._press_color
            fg = self._fg_color
        elif self._hovered:
            bg = self._hover_color
            fg = self._fg_color
        else:
            bg = self._bg_color
            fg = self._fg_color

        # Draw glow effect if enabled and hovered/pressed
        if self._glow and self._enabled and (self._hovered or self._pressed):
            glow_pad = 4
            for i in range(3, 0, -1):
                alpha_color = lighten_color(self._glow_color, 0.3 + i * 0.1)
                create_rounded_rect(
                    self,
                    glow_pad - i * 2,
                    glow_pad - i * 2,
                    self._width - glow_pad + i * 2,
                    self._height - glow_pad + i * 2,
                    self._corner_radius + i,
                    fill=alpha_color,
                    outline=''
                )

        # Draw button background
        pad = 2 if self._pressed and self._enabled else 0
        create_rounded_rect(
            self,
            2, 2 + pad,
            self._width - 2, self._height - 2 + pad,
            self._corner_radius,
            fill=bg,
            outline=darken_color(bg, 0.2) if self._enabled else ''
        )

        # Draw text
        self.create_text(
            self._width // 2,
            self._height // 2 + pad,
            text=self._text,
            fill=fg,
            font=self._font
        )

    def _on_enter(self, event):
        if self._enabled:
            self._hovered = True
            self._draw()

    def _on_leave(self, event):
        self._hovered = False
        self._pressed = False
        self._draw()

    def _on_press(self, event):
        if self._enabled:
            self._pressed = True
            self._draw()
            if self._command:
                self._command()

    def _on_release(self, event):
        self._pressed = False
        self._draw()

    def set_enabled(self, enabled: bool):
        """Enable or disable the button."""
        self._enabled = enabled
        self.configure(cursor='hand2' if enabled else 'arrow')
        self._draw()

    def set_text(self, text: str):
        """Update button text."""
        self._text = text
        self._draw()

    def set_pressed(self, pressed: bool):
        """Set pressed state (for hold buttons)."""
        self._pressed = pressed
        self._draw()

    def configure_colors(self, bg_color: str = None, hover_color: str = None,
                         press_color: str = None, fg_color: str = None):
        """Update button colors."""
        if bg_color:
            self._bg_color = bg_color
            self._hover_color = hover_color or lighten_color(bg_color, 0.15)
            self._press_color = press_color or darken_color(bg_color, 0.1)
        if fg_color:
            self._fg_color = fg_color
        self._draw()


class HoldButton(ModernButton):
    """
    Button that triggers on press and release for hold functionality.
    """

    def __init__(
        self,
        parent,
        text: str,
        on_press: Optional[Callable] = None,
        on_release: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, text, command=None, **kwargs)
        self._on_press_callback = on_press
        self._on_release_callback = on_release

    def _on_press(self, event):
        if self._enabled:
            self._pressed = True
            self._draw()
            if self._on_press_callback:
                self._on_press_callback()

    def _on_release(self, event):
        if self._pressed:
            self._pressed = False
            self._draw()
            if self._on_release_callback:
                self._on_release_callback()

    def trigger_press(self):
        """Programmatically trigger press."""
        if self._enabled and not self._pressed:
            self._pressed = True
            self._draw()
            if self._on_press_callback:
                self._on_press_callback()

    def trigger_release(self):
        """Programmatically trigger release."""
        if self._pressed:
            self._pressed = False
            self._draw()
            if self._on_release_callback:
                self._on_release_callback()


class LEDIndicator(tk.Canvas):
    """
    LED-style status indicator with glow effect.
    """

    def __init__(
        self,
        parent,
        size: int = 16,
        color: str = None,
        bg: str = None
    ):
        color = color or COLORS['status_disabled']
        bg = bg or COLORS['bg_panel']

        super().__init__(
            parent,
            width=size + 8,
            height=size + 8,
            bg=bg,
            highlightthickness=0
        )

        self._size = size
        self._color = color
        self._bg = bg
        self._glowing = False

        self._draw()

    def _draw(self):
        """Draw the LED indicator."""
        self.delete('all')

        cx = (self._size + 8) // 2
        cy = (self._size + 8) // 2
        r = self._size // 2

        # Glow effect layers
        if self._glowing:
            for i in range(4, 0, -1):
                glow_r = r + i * 2
                alpha_color = lighten_color(self._color, 0.2 + i * 0.15)
                self.create_oval(
                    cx - glow_r, cy - glow_r,
                    cx + glow_r, cy + glow_r,
                    fill=alpha_color, outline=''
                )

        # Main LED circle
        self.create_oval(
            cx - r, cy - r,
            cx + r, cy + r,
            fill=self._color,
            outline=darken_color(self._color, 0.3)
        )

        # Highlight spot (gives 3D effect)
        highlight_r = r // 3
        self.create_oval(
            cx - r + 2, cy - r + 2,
            cx - r + 2 + highlight_r, cy - r + 2 + highlight_r,
            fill=lighten_color(self._color, 0.4),
            outline=''
        )

    def set_color(self, color: str, glowing: bool = False):
        """Set the LED color and glow state."""
        self._color = color
        self._glowing = glowing
        self._draw()

    def set_state(self, state: str):
        """Set state by name: 'idle', 'jog', 'move', 'error', 'disabled'."""
        state_colors = {
            'idle': (COLORS['status_idle'], True),
            'connected': (COLORS['status_idle'], True),
            'jog': (COLORS['status_jog'], True),
            'move': (COLORS['status_move'], True),
            'error': (COLORS['status_error'], True),
            'warning': (COLORS['status_warning'], True),
            'disabled': (COLORS['status_disabled'], False),
            'disconnected': (COLORS['status_disabled'], False),
            'connecting': (COLORS['status_warning'], True),
        }
        color, glow = state_colors.get(state.lower(), (COLORS['status_disabled'], False))
        self.set_color(color, glow)


class ModernPanel(ttk.Frame):
    """
    Modern styled panel with dark background and optional accent header.
    """

    def __init__(
        self,
        parent,
        title: str = None,
        accent_color: str = None,
        padding: int = None
    ):
        super().__init__(parent, style='Card.TFrame')

        accent_color = accent_color or COLORS['text_accent']
        padding = padding or 10

        self._title = title
        self._accent_color = accent_color
        self._padding = padding

        self._content_frame = ttk.Frame(self, style='Card.TFrame')

        if title:
            # Create header with accent bar
            header_frame = tk.Frame(self, bg=COLORS['bg_panel'], height=28)
            header_frame.pack(fill='x', padx=1, pady=(1, 0))
            header_frame.pack_propagate(False)

            # Accent bar on left
            accent_bar = tk.Frame(header_frame, bg=accent_color, width=3)
            accent_bar.pack(side='left', fill='y')

            # Title label
            title_label = tk.Label(
                header_frame,
                text=title,
                font=FONTS['heading'],
                fg=accent_color,
                bg=COLORS['bg_panel'],
                padx=8
            )
            title_label.pack(side='left', pady=4)

            self._content_frame.pack(fill='both', expand=True, padx=1, pady=(0, 1))
        else:
            self._content_frame.pack(fill='both', expand=True, padx=1, pady=1)

        # Configure content frame padding
        self._content_frame.configure(padding=padding)

    @property
    def content(self) -> ttk.Frame:
        """Return the content frame for adding widgets."""
        return self._content_frame


class ModernEntry(tk.Entry):
    """
    Entry field with dark styling and focus glow effect.
    """

    def __init__(
        self,
        parent,
        width: int = 20,
        font: tuple = None,
        **kwargs
    ):
        font = font or FONTS['body']

        super().__init__(
            parent,
            width=width,
            font=font,
            bg=COLORS['bg_input'],
            fg=COLORS['text_primary'],
            insertbackground=COLORS['text_accent'],
            relief='flat',
            highlightthickness=2,
            highlightbackground=COLORS['border'],
            highlightcolor=COLORS['border_focus'],
            **kwargs
        )

    def set_enabled(self, enabled: bool):
        """Enable or disable the entry."""
        if enabled:
            self.configure(
                state='normal',
                bg=COLORS['bg_input'],
                fg=COLORS['text_primary']
            )
        else:
            self.configure(
                state='disabled',
                bg=COLORS['bg_panel'],
                fg=COLORS['text_muted']
            )


class ModernScale(tk.Canvas):
    """
    Custom slider with modern styling.
    """

    def __init__(
        self,
        parent,
        from_: float = 0,
        to: float = 100,
        value: float = None,
        command: Optional[Callable[[float], None]] = None,
        width: int = 150,
        height: int = 24,
        track_color: str = None,
        thumb_color: str = None,
        bg: str = None
    ):
        track_color = track_color or COLORS['bg_input']
        thumb_color = thumb_color or COLORS['accent_cyan']
        bg = bg or COLORS['bg_panel']
        value = value if value is not None else from_

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            cursor='hand2'
        )

        self._from = from_
        self._to = to
        self._value = value
        self._command = command
        self._width = width
        self._height = height
        self._track_color = track_color
        self._thumb_color = thumb_color
        self._enabled = True
        self._dragging = False

        self._draw()

        self.bind('<Button-1>', self._on_click)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)

    def _draw(self):
        """Draw the slider."""
        self.delete('all')

        track_height = 4
        thumb_radius = 6
        track_y = self._height // 2
        track_x1 = thumb_radius + 4
        track_x2 = self._width - thumb_radius - 4

        # Track background
        self.create_rectangle(
            track_x1, track_y - track_height // 2,
            track_x2, track_y + track_height // 2,
            fill=self._track_color,
            outline=''
        )

        # Value position
        ratio = (self._value - self._from) / (self._to - self._from) if self._to != self._from else 0
        thumb_x = track_x1 + ratio * (track_x2 - track_x1)

        # Filled portion
        fill_color = self._thumb_color if self._enabled else COLORS['status_disabled']
        self.create_rectangle(
            track_x1, track_y - track_height // 2,
            thumb_x, track_y + track_height // 2,
            fill=fill_color,
            outline=''
        )

        # Thumb glow (subtle, fits within bounds)
        if self._enabled:
            glow_r = thumb_radius + 2
            alpha_color = lighten_color(self._thumb_color, 0.4)
            self.create_oval(
                thumb_x - glow_r, track_y - glow_r,
                thumb_x + glow_r, track_y + glow_r,
                fill=alpha_color, outline=''
            )

        # Thumb
        self.create_oval(
            thumb_x - thumb_radius, track_y - thumb_radius,
            thumb_x + thumb_radius, track_y + thumb_radius,
            fill=fill_color,
            outline=darken_color(fill_color, 0.2)
        )

    def _get_value_from_x(self, x: int) -> float:
        """Convert x coordinate to value."""
        thumb_radius = 6
        track_x1 = thumb_radius + 4
        track_x2 = self._width - thumb_radius - 4

        ratio = (x - track_x1) / (track_x2 - track_x1)
        ratio = max(0, min(1, ratio))
        return self._from + ratio * (self._to - self._from)

    def _on_click(self, event):
        if self._enabled:
            self._dragging = True
            self._value = self._get_value_from_x(event.x)
            self._draw()
            if self._command:
                self._command(self._value)

    def _on_drag(self, event):
        if self._enabled and self._dragging:
            self._value = self._get_value_from_x(event.x)
            self._draw()
            if self._command:
                self._command(self._value)

    def _on_release(self, event):
        self._dragging = False

    def get(self) -> float:
        """Get current value."""
        return self._value

    def set(self, value: float):
        """Set value."""
        self._value = max(self._from, min(self._to, value))
        self._draw()

    def set_enabled(self, enabled: bool):
        """Enable or disable the slider."""
        self._enabled = enabled
        self.configure(cursor='hand2' if enabled else 'arrow')
        self._draw()


class DigitalDisplay(tk.Frame):
    """
    LCD-style digital display for numeric values.
    """

    def __init__(
        self,
        parent,
        label: str = None,
        value: str = "---",
        unit: str = None,
        font: tuple = None,
        fg_color: str = None,
        width: int = None
    ):
        super().__init__(parent, bg=COLORS['bg_display'])

        font = font or FONTS['display_large']
        fg_color = fg_color or COLORS['accent_green']

        self._fg_color = fg_color

        # Optional label above
        if label:
            label_widget = tk.Label(
                self,
                text=label,
                font=FONTS['small'],
                fg=COLORS['text_secondary'],
                bg=COLORS['bg_display']
            )
            label_widget.pack(anchor='w', padx=8, pady=(4, 0))

        # Value frame
        value_frame = tk.Frame(self, bg=COLORS['bg_display'])
        value_frame.pack(fill='x', padx=8, pady=(2, 4))

        # Value label
        self._value_var = tk.StringVar(value=value)
        self._value_label = tk.Label(
            value_frame,
            textvariable=self._value_var,
            font=font,
            fg=fg_color,
            bg=COLORS['bg_display']
        )
        if width:
            self._value_label.configure(width=width, anchor='e')
        self._value_label.pack(side='left')

        # Unit label
        if unit:
            unit_label = tk.Label(
                value_frame,
                text=unit,
                font=FONTS['small'],
                fg=COLORS['text_secondary'],
                bg=COLORS['bg_display']
            )
            unit_label.pack(side='left', padx=(8, 0), pady=(0, 0))

    def set_value(self, value: str):
        """Update the displayed value."""
        self._value_var.set(value)

    def set_color(self, color: str):
        """Update the value color."""
        self._fg_color = color
        self._value_label.configure(fg=color)
