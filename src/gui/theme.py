"""
Modern Dark Theme Configuration

Provides color scheme, fonts, spacing, and ttk style configuration
for the "Industrial Neon" theme.
"""

import tkinter as tk
from tkinter import ttk


# =============================================================================
# COLOR SCHEME
# =============================================================================

COLORS = {
    # Backgrounds
    'bg_dark': '#0d1117',           # Main window background
    'bg_panel': '#161b22',          # Panel/card background
    'bg_input': '#0d1117',          # Entry fields, display areas
    'bg_header': '#21262d',         # Header bar background
    'bg_display': '#010409',        # Digital display background

    # Borders & Accents
    'border': '#30363d',            # Panel borders
    'border_light': '#484f58',      # Lighter borders
    'border_focus': '#58a6ff',      # Focused element border
    'accent_cyan': '#58a6ff',       # Primary accent (blue)
    'accent_green': '#3fb950',      # Success accent
    'accent_glow': '#79c0ff',       # Glow effects

    # Text
    'text_primary': '#e6edf3',      # Primary text
    'text_secondary': '#8b949e',    # Secondary/dim text
    'text_muted': '#6e7681',        # Muted text
    'text_accent': '#58a6ff',       # Accent text

    # Status Colors
    'status_idle': '#3fb950',       # Green - Idle/OK
    'status_jog': '#f0883e',        # Orange - Jogging
    'status_move': '#58a6ff',       # Blue - Moving
    'status_error': '#f85149',      # Red - Error/Stop
    'status_warning': '#d29922',    # Yellow - Warning
    'status_disabled': '#484f58',   # Gray - Disabled

    # Button Colors
    'btn_primary': '#238636',       # Primary action (green)
    'btn_primary_hover': '#2ea043',
    'btn_primary_press': '#238636',
    'btn_secondary': '#21262d',     # Secondary action
    'btn_secondary_hover': '#30363d',
    'btn_danger': '#da3633',        # Danger/Stop
    'btn_danger_hover': '#f85149',
    'btn_jog': '#1f6feb',           # Jog button
    'btn_jog_hover': '#388bfd',
    'btn_jog_press': '#1158c7',
    'btn_up': '#238636',            # Up button (green)
    'btn_up_hover': '#2ea043',
    'btn_down': '#9e6a03',          # Down button (amber)
    'btn_down_hover': '#bb8009',

    # Special
    'glow_green': '#3fb950',
    'glow_blue': '#58a6ff',
    'glow_orange': '#f0883e',
    'glow_red': '#f85149',
}


# =============================================================================
# FONTS
# =============================================================================

FONTS = {
    # Display fonts (for numerical readouts)
    'display_large': ('Consolas', 32, 'bold'),
    'display_medium': ('Consolas', 18, 'bold'),
    'display_small': ('Consolas', 12),

    # UI fonts
    'heading': ('Segoe UI', 11, 'bold'),
    'subheading': ('Segoe UI', 10, 'bold'),
    'body': ('Segoe UI', 9),
    'small': ('Segoe UI', 8),
    'button': ('Segoe UI', 10, 'bold'),
    'button_large': ('Segoe UI', 12, 'bold'),

    # Monospace
    'mono': ('Consolas', 9),
    'mono_small': ('Consolas', 8),
}


# =============================================================================
# SPACING
# =============================================================================

SPACING = {
    'window_padding': 8,
    'panel_gap': 6,
    'panel_padding': 12,
    'element_gap': 8,
    'button_gap': 4,
    'label_gap': 4,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string."""
    return f'#{r:02x}{g:02x}{b:02x}'


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Lighten a hex color by a factor (0-1)."""
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return rgb_to_hex(r, g, b)


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Darken a hex color by a factor (0-1)."""
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return rgb_to_hex(r, g, b)


def create_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle on a canvas."""
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# =============================================================================
# TTK THEME CONFIGURATION
# =============================================================================

def configure_modern_theme(root: tk.Tk) -> None:
    """Configure ttk styles for the modern dark theme."""
    style = ttk.Style()

    # Use 'clam' theme as base (most customizable)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass  # Fall back to default if clam not available

    # Configure root window
    root.configure(bg=COLORS['bg_dark'])

    # === TFrame ===
    style.configure('TFrame', background=COLORS['bg_dark'])
    style.configure('Card.TFrame', background=COLORS['bg_panel'])
    style.configure('Header.TFrame', background=COLORS['bg_header'])

    # === TLabel ===
    style.configure('TLabel',
        background=COLORS['bg_dark'],
        foreground=COLORS['text_primary'],
        font=FONTS['body']
    )
    style.configure('Panel.TLabel',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['body']
    )
    style.configure('Heading.TLabel',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_accent'],
        font=FONTS['heading']
    )
    style.configure('Secondary.TLabel',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_secondary'],
        font=FONTS['small']
    )
    style.configure('Display.TLabel',
        background=COLORS['bg_display'],
        foreground=COLORS['accent_green'],
        font=FONTS['display_medium']
    )

    # === TButton ===
    style.configure('TButton',
        background=COLORS['btn_secondary'],
        foreground=COLORS['text_primary'],
        font=FONTS['button'],
        padding=(12, 6),
        borderwidth=1,
        relief='flat'
    )
    style.map('TButton',
        background=[
            ('active', COLORS['btn_secondary_hover']),
            ('pressed', COLORS['btn_secondary']),
            ('disabled', COLORS['status_disabled'])
        ],
        foreground=[
            ('disabled', COLORS['text_muted'])
        ]
    )

    # Primary button style
    style.configure('Primary.TButton',
        background=COLORS['btn_primary'],
        foreground='white'
    )
    style.map('Primary.TButton',
        background=[
            ('active', COLORS['btn_primary_hover']),
            ('pressed', COLORS['btn_primary_press']),
            ('disabled', COLORS['status_disabled'])
        ]
    )

    # Danger button style
    style.configure('Danger.TButton',
        background=COLORS['btn_danger'],
        foreground='white'
    )
    style.map('Danger.TButton',
        background=[
            ('active', COLORS['btn_danger_hover']),
            ('disabled', COLORS['status_disabled'])
        ]
    )

    # === TEntry ===
    style.configure('TEntry',
        fieldbackground=COLORS['bg_input'],
        foreground=COLORS['text_primary'],
        insertcolor=COLORS['text_accent'],
        borderwidth=1,
        padding=6
    )
    style.map('TEntry',
        fieldbackground=[
            ('disabled', COLORS['bg_panel']),
            ('readonly', COLORS['bg_panel'])
        ],
        foreground=[
            ('disabled', COLORS['text_muted'])
        ]
    )

    # === TCombobox ===
    style.configure('TCombobox',
        fieldbackground=COLORS['bg_input'],
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        arrowcolor=COLORS['text_secondary'],
        borderwidth=1,
        padding=4
    )
    style.map('TCombobox',
        fieldbackground=[
            ('disabled', COLORS['bg_panel']),
            ('readonly', COLORS['bg_input'])
        ],
        foreground=[
            ('disabled', COLORS['text_muted'])
        ],
        arrowcolor=[
            ('disabled', COLORS['text_muted'])
        ]
    )

    # === TLabelframe ===
    style.configure('TLabelframe',
        background=COLORS['bg_panel'],
        bordercolor=COLORS['border'],
        relief='solid',
        borderwidth=1
    )
    style.configure('TLabelframe.Label',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_accent'],
        font=FONTS['heading']
    )

    # === TScale (slider) ===
    style.configure('TScale',
        background=COLORS['bg_panel'],
        troughcolor=COLORS['bg_input'],
        sliderlength=20,
        borderwidth=0
    )
    style.configure('Horizontal.TScale',
        background=COLORS['bg_panel']
    )

    # === TRadiobutton ===
    style.configure('TRadiobutton',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['body'],
        indicatorcolor=COLORS['bg_input']
    )
    style.map('TRadiobutton',
        background=[
            ('active', COLORS['bg_panel'])
        ],
        indicatorcolor=[
            ('selected', COLORS['accent_cyan'])
        ]
    )

    # === TCheckbutton ===
    style.configure('TCheckbutton',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['body'],
        indicatorcolor=COLORS['bg_input']
    )
    style.map('TCheckbutton',
        background=[
            ('active', COLORS['bg_panel'])
        ],
        indicatorcolor=[
            ('selected', COLORS['accent_cyan'])
        ]
    )

    # === TSeparator ===
    style.configure('TSeparator',
        background=COLORS['border']
    )

    # === TSpinbox ===
    style.configure('TSpinbox',
        fieldbackground=COLORS['bg_input'],
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        arrowcolor=COLORS['text_secondary'],
        borderwidth=1,
        padding=4
    )
    style.map('TSpinbox',
        fieldbackground=[
            ('disabled', COLORS['bg_panel'])
        ],
        foreground=[
            ('disabled', COLORS['text_muted'])
        ]
    )

    # === TNotebook ===
    style.configure('TNotebook',
        background=COLORS['bg_dark'],
        borderwidth=0
    )
    style.configure('TNotebook.Tab',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_secondary'],
        padding=(12, 6),
        font=FONTS['body']
    )
    style.map('TNotebook.Tab',
        background=[
            ('selected', COLORS['bg_header']),
            ('active', COLORS['bg_header'])
        ],
        foreground=[
            ('selected', COLORS['text_primary'])
        ]
    )

    # === Scrollbar ===
    style.configure('Vertical.TScrollbar',
        background=COLORS['bg_panel'],
        troughcolor=COLORS['bg_dark'],
        borderwidth=0,
        arrowcolor=COLORS['text_secondary']
    )
    style.configure('Horizontal.TScrollbar',
        background=COLORS['bg_panel'],
        troughcolor=COLORS['bg_dark'],
        borderwidth=0,
        arrowcolor=COLORS['text_secondary']
    )
