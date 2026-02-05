"""
Camera Panel

Displays MJPEG stream from ESP32-CAM with controls for flash,
snapshot capture, and auto-discovery.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import io
import time
from typing import Optional, List

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..camera_manager import (
    CameraConfig,
    MJPEGStreamReader,
    CameraDiscovery,
)
from ..config import (
    CAMERA_DISPLAY_SIZES,
    CAMERA_DEFAULT_SIZE,
    CAMERA_1_HOST,
    CAMERA_2_HOST,
)
from .theme import COLORS, FONTS
from .widgets import ModernButton, ModernPanel, LEDIndicator


class CameraPanel(tk.Frame):
    """
    Camera panel displaying MJPEG stream from ESP32-CAM.

    Features:
    - Auto-discovery of cameras on local network
    - Manual IP entry
    - Selectable display sizes
    - Flash toggle
    - Snapshot capture and save
    """

    SIZES = CAMERA_DISPLAY_SIZES
    DEFAULT_SIZE = CAMERA_DEFAULT_SIZE

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], **kwargs)

        if not PIL_AVAILABLE:
            self._show_pil_error()
            return

        self._config: Optional[CameraConfig] = None
        self._stream_reader: Optional[MJPEGStreamReader] = None
        self._connected = False
        self._current_frame: Optional[bytes] = None
        self._photo_image: Optional[ImageTk.PhotoImage] = None
        self._display_size = self.SIZES[self.DEFAULT_SIZE]
        self._flash_on = False
        self._discovered_ips: List[str] = []
        self._scan_thread: Optional[threading.Thread] = None

        self._create_widgets()

    def _show_pil_error(self):
        """Show error when PIL/Pillow is not installed."""
        error_frame = tk.Frame(self, bg=COLORS['bg_panel'], padx=20, pady=20)
        error_frame.pack(fill='both', expand=True, padx=5, pady=5)

        tk.Label(
            error_frame,
            text="Camera Unavailable",
            font=FONTS['heading'],
            fg=COLORS['status_error'],
            bg=COLORS['bg_panel']
        ).pack(pady=(0, 10))

        tk.Label(
            error_frame,
            text="Pillow library is required.\nRun: pip install Pillow",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        ).pack()

    def _create_widgets(self):
        """Create all panel widgets."""
        # Main panel container (fixed size, no expand)
        self._panel = ModernPanel(self, title="Camera", accent_color=COLORS['accent_cyan'])
        self._panel.pack(padx=5, pady=5)

        content = self._panel.content

        # Connection section
        self._create_connection_section(content)

        # Video display
        self._create_video_display(content)

        # Controls section
        self._create_controls_section(content)

        # Status section
        self._create_status_section(content)

    def _create_connection_section(self, parent):
        """Create connection controls."""
        conn_frame = tk.Frame(parent, bg=COLORS['bg_panel'])
        conn_frame.pack(fill='x', pady=(0, 8))

        # IP selection row
        ip_row = tk.Frame(conn_frame, bg=COLORS['bg_panel'])
        ip_row.pack(fill='x')

        tk.Label(
            ip_row,
            text="Camera IP:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        ).pack(side='left', padx=(0, 6))

        # IP combo/entry - pre-populate with configured camera IPs
        self._ip_var = tk.StringVar(value=CAMERA_1_HOST)
        self._ip_combo = ttk.Combobox(
            ip_row,
            textvariable=self._ip_var,
            width=15,
            values=[CAMERA_1_HOST, CAMERA_2_HOST]
        )
        self._ip_combo.pack(side='left', padx=(0, 6))

        # Scan button
        self._scan_btn = ModernButton(
            ip_row,
            text="Scan",
            command=self._start_scan,
            width=60,
            height=28,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['body']
        )
        self._scan_btn.pack(side='left', padx=(0, 6))

        # Size selector
        tk.Label(
            ip_row,
            text="Size:",
            font=FONTS['body'],
            fg=COLORS['text_secondary'],
            bg=COLORS['bg_panel']
        ).pack(side='left', padx=(8, 6))

        self._size_var = tk.StringVar(value=self.DEFAULT_SIZE)
        self._size_combo = ttk.Combobox(
            ip_row,
            textvariable=self._size_var,
            values=list(self.SIZES.keys()),
            width=10,
            state='readonly'
        )
        self._size_combo.pack(side='left')
        self._size_combo.bind('<<ComboboxSelected>>', self._on_size_change)

        # Connect button row
        btn_row = tk.Frame(conn_frame, bg=COLORS['bg_panel'])
        btn_row.pack(fill='x', pady=(8, 0))

        self._connect_btn = ModernButton(
            btn_row,
            text="Connect",
            command=self._toggle_connection,
            width=100,
            height=32,
            bg_color=COLORS['btn_primary'],
            glow=True,
            font=FONTS['button']
        )
        self._connect_btn.pack(side='left')

        # Connection LED
        self._conn_led = LEDIndicator(btn_row, size=12)
        self._conn_led.pack(side='left', padx=(12, 0))
        self._conn_led.set_state('disconnected')

    def _create_video_display(self, parent):
        """Create the video display area."""
        # Display frame with border (fixed size, no expand)
        display_outer = tk.Frame(parent, bg=COLORS['border'], padx=2, pady=2)
        display_outer.pack(pady=8)

        self._display_frame = tk.Frame(display_outer, bg=COLORS['bg_display'], width=240, height=180)
        self._display_frame.pack()
        self._display_frame.pack_propagate(False)  # Prevent children from resizing frame

        # Video label
        self._video_label = tk.Label(
            self._display_frame,
            bg=COLORS['bg_display'],
            text="No Camera Connected",
            font=FONTS['body'],
            fg=COLORS['text_muted']
        )
        self._video_label.place(relx=0.5, rely=0.5, anchor='center')

        # Set initial size
        self._update_display_size()

    def _create_controls_section(self, parent):
        """Create camera control buttons."""
        controls_frame = tk.Frame(parent, bg=COLORS['bg_panel'])
        controls_frame.pack(fill='x', pady=(0, 8))

        # Flash button
        self._flash_btn = ModernButton(
            controls_frame,
            text="Flash Off",
            command=self._toggle_flash,
            width=80,
            height=32,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['button']
        )
        self._flash_btn.pack(side='left', padx=(0, 8))
        self._flash_btn.set_enabled(False)

        # Capture button
        self._capture_btn = ModernButton(
            controls_frame,
            text="Capture",
            command=self._capture_snapshot,
            width=80,
            height=32,
            bg_color=COLORS['btn_jog'],
            font=FONTS['button']
        )
        self._capture_btn.pack(side='left', padx=(0, 8))
        self._capture_btn.set_enabled(False)

        # Save button
        self._save_btn = ModernButton(
            controls_frame,
            text="Save",
            command=self._save_snapshot,
            width=80,
            height=32,
            bg_color=COLORS['btn_secondary'],
            font=FONTS['button']
        )
        self._save_btn.pack(side='left')
        self._save_btn.set_enabled(False)

    def _create_status_section(self, parent):
        """Create status display."""
        status_frame = tk.Frame(parent, bg=COLORS['bg_panel'])
        status_frame.pack(fill='x')

        self._status_var = tk.StringVar(value="Disconnected")
        self._status_label = tk.Label(
            status_frame,
            textvariable=self._status_var,
            font=FONTS['small'],
            fg=COLORS['text_muted'],
            bg=COLORS['bg_panel']
        )
        self._status_label.pack(side='left')

    def _start_scan(self):
        """Start scanning for cameras on the network."""
        local_ip = CameraDiscovery.get_local_ip()
        if not local_ip:
            self._status_var.set("Could not determine local IP")
            return

        self._discovered_ips = []
        self._ip_combo['values'] = []
        self._status_var.set("Scanning network...")
        self._scan_btn.set_enabled(False)

        def on_found(ip: str):
            self._discovered_ips.append(ip)
            self.after(0, self._update_discovered_ips)

        def on_complete():
            self.after(0, self._scan_complete)

        self._scan_thread = CameraDiscovery.scan_subnet(
            local_ip, on_found, on_complete
        )

    def _update_discovered_ips(self):
        """Update the IP combo with discovered cameras."""
        self._ip_combo['values'] = self._discovered_ips
        if self._discovered_ips and not self._ip_var.get():
            self._ip_var.set(self._discovered_ips[0])
        self._status_var.set(f"Found {len(self._discovered_ips)} camera(s)...")

    def _scan_complete(self):
        """Handle scan completion."""
        self._scan_btn.set_enabled(True)
        count = len(self._discovered_ips)
        if count == 0:
            self._status_var.set("No cameras found")
        else:
            self._status_var.set(f"Found {count} camera(s)")

    def _toggle_connection(self):
        """Connect or disconnect from camera."""
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        """Connect to the camera."""
        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showwarning("No IP", "Please enter or select a camera IP address.")
            return

        self._config = CameraConfig(ip=ip)
        stream_url = f"http://{ip}:81/stream"

        self._status_var.set(f"Connecting to {ip}...")
        self._conn_led.set_state('connecting')

        self._stream_reader = MJPEGStreamReader(
            stream_url,
            on_frame=self._on_frame_received,
            on_error=self._on_stream_error
        )
        self._stream_reader.start()

        self._connected = True
        self._connect_btn.set_text("Disconnect")
        self._connect_btn.configure_colors(bg_color=COLORS['btn_danger'])
        self._flash_btn.set_enabled(True)
        self._capture_btn.set_enabled(True)

    def _disconnect(self):
        """Disconnect from the camera."""
        if self._stream_reader:
            self._stream_reader.stop()
            self._stream_reader = None

        self._connected = False
        self._config = None
        self._current_frame = None
        self._flash_on = False

        self._connect_btn.set_text("Connect")
        self._connect_btn.configure_colors(bg_color=COLORS['btn_primary'])
        self._conn_led.set_state('disconnected')
        self._flash_btn.set_text("Flash Off")
        self._flash_btn.set_enabled(False)
        self._capture_btn.set_enabled(False)
        self._save_btn.set_enabled(False)
        self._status_var.set("Disconnected")

        self._video_label.configure(
            image='',
            text="No Camera Connected"
        )
        self._photo_image = None

    def _on_frame_received(self, frame_data: bytes):
        """Handle received frame from stream (called from background thread)."""
        self._current_frame = frame_data
        self.after(0, self._display_frame_data, frame_data)

    def _display_frame_data(self, frame_data: bytes):
        """Display frame data in the video label (called on main thread)."""
        try:
            # Decode JPEG
            image = Image.open(io.BytesIO(frame_data))

            # Resize if needed
            if self._display_size:
                image = image.resize(self._display_size, Image.Resampling.LANCZOS)
            else:
                # Fit mode - scale to fit container
                container_w = self._display_frame.winfo_width()
                container_h = self._display_frame.winfo_height()
                if container_w > 1 and container_h > 1:
                    img_w, img_h = image.size
                    scale = min(container_w / img_w, container_h / img_h)
                    new_size = (int(img_w * scale), int(img_h * scale))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            self._photo_image = ImageTk.PhotoImage(image)
            self._video_label.configure(image=self._photo_image, text='')

            # Update status
            if self._connected:
                self._conn_led.set_state('connected')
                self._status_var.set(f"Connected - {image.size[0]}x{image.size[1]}")

        except Exception as e:
            pass  # Silently ignore decode errors for individual frames

    def _on_stream_error(self, error: str):
        """Handle stream error (called from background thread)."""
        self.after(0, self._handle_stream_error, error)

    def _handle_stream_error(self, error: str):
        """Handle stream error on main thread."""
        self._disconnect()
        self._status_var.set(f"Error: {error}")
        messagebox.showerror("Camera Error", error)

    def _on_size_change(self, event=None):
        """Handle display size change."""
        size_name = self._size_var.get()
        self._display_size = self.SIZES.get(size_name)
        self._update_display_size()

    def _update_display_size(self):
        """Update the display frame size."""
        if self._display_size:
            w, h = self._display_size
            self._display_frame.configure(width=w, height=h)
            self._video_label.configure(width=w, height=h)
        else:
            # Fit mode - no fixed size
            self._display_frame.configure(width=320, height=240)

    def _toggle_flash(self):
        """Toggle the camera flash."""
        if not self._config:
            return

        def send_flash():
            try:
                url = f"http://{self._config.ip}/flash"
                with urllib.request.urlopen(url, timeout=5) as response:
                    result = response.read().decode()
                    self.after(0, self._update_flash_state, 'ON' in result)
            except Exception as e:
                self.after(0, lambda: self._status_var.set(f"Flash error: {e}"))

        threading.Thread(target=send_flash, daemon=True).start()

    def _update_flash_state(self, is_on: bool):
        """Update flash button state."""
        self._flash_on = is_on
        self._flash_btn.set_text("Flash On" if is_on else "Flash Off")
        if is_on:
            self._flash_btn.configure_colors(bg_color=COLORS['status_warning'])
        else:
            self._flash_btn.configure_colors(bg_color=COLORS['btn_secondary'])

    def _capture_snapshot(self):
        """Capture a snapshot from the current stream."""
        if self._current_frame:
            self._save_btn.set_enabled(True)
            self._status_var.set("Snapshot captured - click Save to save")

    def _save_snapshot(self):
        """Save the captured snapshot to a file."""
        if not self._current_frame:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[
                ("JPEG files", "*.jpg"),
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ],
            initialfile=f"snapshot_{int(time.time())}.jpg"
        )

        if filename:
            try:
                image = Image.open(io.BytesIO(self._current_frame))
                image.save(filename)
                self._status_var.set(f"Saved: {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save image: {e}")

    def destroy(self):
        """Clean up resources when panel is destroyed."""
        self._disconnect()
        super().destroy()
