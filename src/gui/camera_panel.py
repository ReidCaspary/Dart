"""
Camera Panel

Displays MJPEG stream from ESP32-CAM and RTSP stream from TAPO cameras.
Settings accessible via gear icon in the panel header.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import io
import time
import threading
import urllib.request
from typing import Optional, List

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..camera_manager import (
    CameraConfig,
    MJPEGStreamReader,
    RTSPStreamReader,
    CameraDiscovery,
)
from ..config import (
    CAMERA_DISPLAY_SIZES,
    CAMERA_DEFAULT_SIZE,
    TAPO_RTSP_PORT,
)
from .theme import COLORS, FONTS
from .widgets import ModernButton, LEDIndicator


class CameraPanel(tk.Frame):
    """
    ESP32-CAM panel with compact layout.
    Settings (IP, display size, scan) accessible via gear icon in header.
    """

    SIZES = CAMERA_DISPLAY_SIZES
    DEFAULT_SIZE = CAMERA_DEFAULT_SIZE

    def __init__(self, parent, title="Camera", default_ip="", **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], **kwargs)

        if not PIL_AVAILABLE:
            self._show_pil_error()
            return

        self._title = title
        self._default_ip = default_ip
        self._config: Optional[CameraConfig] = None
        self._stream_reader: Optional[MJPEGStreamReader] = None
        self._connected = False
        self._current_frame: Optional[bytes] = None
        self._photo_image: Optional[ImageTk.PhotoImage] = None
        self._display_size = self.SIZES[self.DEFAULT_SIZE]
        self._flash_on = False
        self._discovered_ips: List[str] = []
        self._scan_thread: Optional[threading.Thread] = None
        self._settings_popup = None

        # StringVars persist across popup open/close
        self._ip_var = tk.StringVar(value=default_ip)
        self._size_var = tk.StringVar(value=self.DEFAULT_SIZE)

        self._create_widgets()

    def _show_pil_error(self):
        error_frame = tk.Frame(self, bg=COLORS['bg_panel'], padx=20, pady=20)
        error_frame.pack(fill='both', expand=True, padx=5, pady=5)
        tk.Label(
            error_frame, text="Camera Unavailable", font=FONTS['heading'],
            fg=COLORS['status_error'], bg=COLORS['bg_panel']
        ).pack(pady=(0, 10))
        tk.Label(
            error_frame, text="Pillow library is required.\nRun: pip install Pillow",
            font=FONTS['body'], fg=COLORS['text_secondary'], bg=COLORS['bg_panel']
        ).pack()

    def _create_widgets(self):
        self._panel_frame = tk.Frame(self, bg=COLORS['bg_panel'])
        self._panel_frame.pack(padx=5, pady=5)

        self._create_header()

        content = tk.Frame(self._panel_frame, bg=COLORS['bg_panel'], padx=10, pady=8)
        content.pack(fill='both')

        self._create_connect_row(content)
        self._create_video_display(content)
        self._create_controls_section(content)
        self._create_status_section(content)

    def _create_header(self):
        header = tk.Frame(self._panel_frame, bg=COLORS['bg_panel'], height=28)
        header.pack(fill='x', padx=1, pady=(1, 0))
        header.pack_propagate(False)

        accent = tk.Frame(header, bg=COLORS['accent_cyan'], width=3)
        accent.pack(side='left', fill='y')

        tk.Label(
            header, text=self._title, font=FONTS['heading'],
            fg=COLORS['accent_cyan'], bg=COLORS['bg_panel'], padx=8
        ).pack(side='left', pady=4)

        ModernButton(
            header, text="\u2699", command=self._show_settings,
            width=28, height=24, bg_color=COLORS['btn_secondary'],
            font=FONTS['body']
        ).pack(side='right', padx=4, pady=2)

    def _create_connect_row(self, parent):
        row = tk.Frame(parent, bg=COLORS['bg_panel'])
        row.pack(fill='x', pady=(0, 8))

        self._connect_btn = ModernButton(
            row, text="Connect", command=self._toggle_connection,
            width=100, height=32, bg_color=COLORS['btn_primary'],
            glow=True, font=FONTS['button']
        )
        self._connect_btn.pack(side='left')

        self._conn_led = LEDIndicator(row, size=12)
        self._conn_led.pack(side='left', padx=(12, 0))
        self._conn_led.set_state('disconnected')

    def _create_video_display(self, parent):
        display_outer = tk.Frame(parent, bg=COLORS['border'], padx=2, pady=2)
        display_outer.pack(pady=8)

        self._display_frame = tk.Frame(display_outer, bg=COLORS['bg_display'], width=240, height=180)
        self._display_frame.pack()
        self._display_frame.pack_propagate(False)

        self._video_label = tk.Label(
            self._display_frame, bg=COLORS['bg_display'],
            text="No Camera Connected", font=FONTS['body'], fg=COLORS['text_muted']
        )
        self._video_label.place(relx=0.5, rely=0.5, anchor='center')
        self._update_display_size()

    def _create_controls_section(self, parent):
        controls_frame = tk.Frame(parent, bg=COLORS['bg_panel'])
        controls_frame.pack(fill='x', pady=(0, 8))

        self._flash_btn = ModernButton(
            controls_frame, text="Flash Off", command=self._toggle_flash,
            width=80, height=32, bg_color=COLORS['btn_secondary'], font=FONTS['button']
        )
        self._flash_btn.pack(side='left', padx=(0, 8))
        self._flash_btn.set_enabled(False)

        self._capture_btn = ModernButton(
            controls_frame, text="Capture", command=self._capture_snapshot,
            width=80, height=32, bg_color=COLORS['btn_jog'], font=FONTS['button']
        )
        self._capture_btn.pack(side='left', padx=(0, 8))
        self._capture_btn.set_enabled(False)

        self._save_btn = ModernButton(
            controls_frame, text="Save", command=self._save_snapshot,
            width=80, height=32, bg_color=COLORS['btn_secondary'], font=FONTS['button']
        )
        self._save_btn.pack(side='left')
        self._save_btn.set_enabled(False)

    def _create_status_section(self, parent):
        status_frame = tk.Frame(parent, bg=COLORS['bg_panel'])
        status_frame.pack(fill='x')

        self._status_var = tk.StringVar(value="Disconnected")
        tk.Label(
            status_frame, textvariable=self._status_var,
            font=FONTS['small'], fg=COLORS['text_muted'], bg=COLORS['bg_panel']
        ).pack(side='left')

    # === Settings Popup ===

    def _show_settings(self):
        if self._settings_popup is not None:
            try:
                if self._settings_popup.winfo_exists():
                    self._settings_popup.destroy()
                    self._settings_popup = None
                    return
            except tk.TclError:
                pass
            self._settings_popup = None

        popup = tk.Toplevel(self)
        popup.title(f"{self._title} Settings")
        popup.configure(bg=COLORS['bg_panel'])
        popup.resizable(False, False)
        popup.attributes('-topmost', True)

        x = self.winfo_rootx() + self.winfo_width() + 5
        y = self.winfo_rooty()
        popup.geometry(f"+{x}+{y}")

        frame = tk.Frame(popup, bg=COLORS['bg_panel'], padx=12, pady=10)
        frame.pack(fill='both')

        # IP
        tk.Label(frame, text="Camera IP:", font=FONTS['body'],
                 fg=COLORS['text_secondary'], bg=COLORS['bg_panel']).pack(anchor='w')

        ip_row = tk.Frame(frame, bg=COLORS['bg_panel'])
        ip_row.pack(fill='x', pady=(2, 8))

        values = [self._default_ip] + self._discovered_ips if self._default_ip else self._discovered_ips
        self._ip_combo = ttk.Combobox(
            ip_row, textvariable=self._ip_var, width=15, values=values
        )
        self._ip_combo.pack(side='left', padx=(0, 6))

        self._scan_btn = ModernButton(
            ip_row, text="Scan", command=self._start_scan,
            width=60, height=28, bg_color=COLORS['btn_secondary'], font=FONTS['body']
        )
        self._scan_btn.pack(side='left')

        # Display Size
        tk.Label(frame, text="Display Size:", font=FONTS['body'],
                 fg=COLORS['text_secondary'], bg=COLORS['bg_panel']).pack(anchor='w')

        size_combo = ttk.Combobox(
            frame, textvariable=self._size_var,
            values=list(self.SIZES.keys()), width=12, state='readonly'
        )
        size_combo.pack(anchor='w', pady=(2, 10))
        size_combo.bind('<<ComboboxSelected>>', self._on_size_change)

        # Close
        ModernButton(
            frame, text="Close", command=self._close_settings,
            width=60, height=28, bg_color=COLORS['btn_secondary'], font=FONTS['body']
        ).pack(anchor='e')

        self._settings_popup = popup
        popup.protocol("WM_DELETE_WINDOW", self._close_settings)

    def _close_settings(self):
        if self._settings_popup:
            try:
                self._settings_popup.destroy()
            except tk.TclError:
                pass
            self._settings_popup = None

    # === Network Scan ===

    def _start_scan(self):
        local_ip = CameraDiscovery.get_local_ip()
        if not local_ip:
            self._status_var.set("Could not determine local IP")
            return

        self._discovered_ips = []
        try:
            self._ip_combo['values'] = []
        except (tk.TclError, AttributeError):
            pass
        self._status_var.set("Scanning network...")
        try:
            self._scan_btn.set_enabled(False)
        except (tk.TclError, AttributeError):
            pass

        def on_found(ip: str):
            self._discovered_ips.append(ip)
            self.after(0, self._update_discovered_ips)

        def on_complete():
            self.after(0, self._scan_complete)

        self._scan_thread = CameraDiscovery.scan_subnet(
            local_ip, on_found, on_complete
        )

    def _update_discovered_ips(self):
        try:
            if hasattr(self, '_ip_combo') and self._ip_combo.winfo_exists():
                values = [self._default_ip] + self._discovered_ips if self._default_ip else self._discovered_ips
                self._ip_combo['values'] = values
                if self._discovered_ips and not self._ip_var.get():
                    self._ip_var.set(self._discovered_ips[0])
        except (tk.TclError, AttributeError):
            pass
        self._status_var.set(f"Found {len(self._discovered_ips)} camera(s)...")

    def _scan_complete(self):
        try:
            if hasattr(self, '_scan_btn') and self._scan_btn.winfo_exists():
                self._scan_btn.set_enabled(True)
        except (tk.TclError, AttributeError):
            pass
        count = len(self._discovered_ips)
        if count == 0:
            self._status_var.set("No cameras found")
        else:
            self._status_var.set(f"Found {count} camera(s)")

    # === Connection ===

    def _toggle_connection(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
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

        self._video_label.configure(image='', text="No Camera Connected")
        self._photo_image = None

    # === Frame Display ===

    def _on_frame_received(self, frame_data: bytes):
        self._current_frame = frame_data
        self.after(0, self._display_frame_data, frame_data)

    def _display_frame_data(self, frame_data: bytes):
        try:
            image = Image.open(io.BytesIO(frame_data))
            if self._display_size:
                image = image.resize(self._display_size, Image.Resampling.LANCZOS)
            else:
                container_w = self._display_frame.winfo_width()
                container_h = self._display_frame.winfo_height()
                if container_w > 1 and container_h > 1:
                    img_w, img_h = image.size
                    scale = min(container_w / img_w, container_h / img_h)
                    new_size = (int(img_w * scale), int(img_h * scale))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)

            self._photo_image = ImageTk.PhotoImage(image)
            self._video_label.configure(image=self._photo_image, text='')

            if self._connected:
                self._conn_led.set_state('connected')
                self._status_var.set(f"Connected - {image.size[0]}x{image.size[1]}")
        except Exception:
            pass

    def _on_stream_error(self, error: str):
        self.after(0, self._handle_stream_error, error)

    def _handle_stream_error(self, error: str):
        self._disconnect()
        self._status_var.set(f"Error: {error}")
        messagebox.showerror("Camera Error", error)

    # === Size ===

    def _on_size_change(self, event=None):
        size_name = self._size_var.get()
        self._display_size = self.SIZES.get(size_name)
        self._update_display_size()

    def _update_display_size(self):
        if self._display_size:
            w, h = self._display_size
            self._display_frame.configure(width=w, height=h)
            self._video_label.configure(width=w, height=h)
        else:
            self._display_frame.configure(width=320, height=240)

    # === Flash ===

    def _toggle_flash(self):
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
        self._flash_on = is_on
        self._flash_btn.set_text("Flash On" if is_on else "Flash Off")
        if is_on:
            self._flash_btn.configure_colors(bg_color=COLORS['status_warning'])
        else:
            self._flash_btn.configure_colors(bg_color=COLORS['btn_secondary'])

    # === Snapshot ===

    def _capture_snapshot(self):
        if self._current_frame:
            self._save_btn.set_enabled(True)
            self._status_var.set("Snapshot captured - click Save to save")

    def _save_snapshot(self):
        if not self._current_frame:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")],
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
        self._close_settings()
        self._disconnect()
        super().destroy()


class TapoCameraPanel(tk.Frame):
    """
    TAPO C120 RTSP camera panel with compact layout.
    Settings (IP, credentials, quality, size) accessible via gear icon in header.
    """

    SIZES = CAMERA_DISPLAY_SIZES
    DEFAULT_SIZE = CAMERA_DEFAULT_SIZE

    QUALITY_OPTIONS = {
        'High (1080p)': 'stream1',
        'Low (360p)': 'stream2',
    }

    def __init__(self, parent, title="TAPO Camera", default_ip="", default_user="", default_pass="", **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], **kwargs)

        if not PIL_AVAILABLE:
            self._show_pil_error()
            return

        self._title = title
        self._default_ip = default_ip
        self._stream_reader: Optional[RTSPStreamReader] = None
        self._connected = False
        self._current_frame: Optional[bytes] = None
        self._photo_image: Optional[ImageTk.PhotoImage] = None
        self._display_size = self.SIZES[self.DEFAULT_SIZE]
        self._settings_popup = None

        # StringVars persist across popup open/close
        self._ip_var = tk.StringVar(value=default_ip)
        self._user_var = tk.StringVar(value=default_user)
        self._pass_var = tk.StringVar(value=default_pass)
        self._quality_var = tk.StringVar(value='High (1080p)')
        self._size_var = tk.StringVar(value=self.DEFAULT_SIZE)

        self._create_widgets()

    def _show_pil_error(self):
        error_frame = tk.Frame(self, bg=COLORS['bg_panel'], padx=20, pady=20)
        error_frame.pack(fill='both', expand=True, padx=5, pady=5)
        tk.Label(
            error_frame, text="Camera Unavailable", font=FONTS['heading'],
            fg=COLORS['status_error'], bg=COLORS['bg_panel']
        ).pack(pady=(0, 10))
        tk.Label(
            error_frame, text="Pillow library is required.\nRun: pip install Pillow",
            font=FONTS['body'], fg=COLORS['text_secondary'], bg=COLORS['bg_panel']
        ).pack()

    def _create_widgets(self):
        self._panel_frame = tk.Frame(self, bg=COLORS['bg_panel'])
        self._panel_frame.pack(padx=5, pady=5)

        self._create_header()

        content = tk.Frame(self._panel_frame, bg=COLORS['bg_panel'], padx=10, pady=8)
        content.pack(fill='both')

        self._create_connect_row(content)
        self._create_video_display(content)
        self._create_controls_section(content)
        self._create_status_section(content)

    def _create_header(self):
        header = tk.Frame(self._panel_frame, bg=COLORS['bg_panel'], height=28)
        header.pack(fill='x', padx=1, pady=(1, 0))
        header.pack_propagate(False)

        accent = tk.Frame(header, bg=COLORS['glow_orange'], width=3)
        accent.pack(side='left', fill='y')

        tk.Label(
            header, text=self._title, font=FONTS['heading'],
            fg=COLORS['glow_orange'], bg=COLORS['bg_panel'], padx=8
        ).pack(side='left', pady=4)

        ModernButton(
            header, text="\u2699", command=self._show_settings,
            width=28, height=24, bg_color=COLORS['btn_secondary'],
            font=FONTS['body']
        ).pack(side='right', padx=4, pady=2)

    def _create_connect_row(self, parent):
        row = tk.Frame(parent, bg=COLORS['bg_panel'])
        row.pack(fill='x', pady=(0, 8))

        self._connect_btn = ModernButton(
            row, text="Connect", command=self._toggle_connection,
            width=100, height=32, bg_color=COLORS['btn_primary'],
            glow=True, font=FONTS['button']
        )
        self._connect_btn.pack(side='left')

        self._conn_led = LEDIndicator(row, size=12)
        self._conn_led.pack(side='left', padx=(12, 0))
        self._conn_led.set_state('disconnected')

    def _create_video_display(self, parent):
        display_outer = tk.Frame(parent, bg=COLORS['border'], padx=2, pady=2)
        display_outer.pack(pady=8)

        self._display_frame = tk.Frame(display_outer, bg=COLORS['bg_display'], width=240, height=180)
        self._display_frame.pack()
        self._display_frame.pack_propagate(False)

        self._video_label = tk.Label(
            self._display_frame, bg=COLORS['bg_display'],
            text="No Camera Connected", font=FONTS['body'], fg=COLORS['text_muted']
        )
        self._video_label.place(relx=0.5, rely=0.5, anchor='center')
        self._update_display_size()

    def _create_controls_section(self, parent):
        controls_frame = tk.Frame(parent, bg=COLORS['bg_panel'])
        controls_frame.pack(fill='x', pady=(0, 8))

        self._capture_btn = ModernButton(
            controls_frame, text="Capture", command=self._capture_snapshot,
            width=80, height=32, bg_color=COLORS['btn_jog'], font=FONTS['button']
        )
        self._capture_btn.pack(side='left', padx=(0, 8))
        self._capture_btn.set_enabled(False)

        self._save_btn = ModernButton(
            controls_frame, text="Save", command=self._save_snapshot,
            width=80, height=32, bg_color=COLORS['btn_secondary'], font=FONTS['button']
        )
        self._save_btn.pack(side='left')
        self._save_btn.set_enabled(False)

    def _create_status_section(self, parent):
        status_frame = tk.Frame(parent, bg=COLORS['bg_panel'])
        status_frame.pack(fill='x')

        self._status_var = tk.StringVar(value="Disconnected")
        tk.Label(
            status_frame, textvariable=self._status_var,
            font=FONTS['small'], fg=COLORS['text_muted'], bg=COLORS['bg_panel']
        ).pack(side='left')

    # === Settings Popup ===

    def _show_settings(self):
        if self._settings_popup is not None:
            try:
                if self._settings_popup.winfo_exists():
                    self._settings_popup.destroy()
                    self._settings_popup = None
                    return
            except tk.TclError:
                pass
            self._settings_popup = None

        popup = tk.Toplevel(self)
        popup.title(f"{self._title} Settings")
        popup.configure(bg=COLORS['bg_panel'])
        popup.resizable(False, False)
        popup.attributes('-topmost', True)

        x = self.winfo_rootx() + self.winfo_width() + 5
        y = self.winfo_rooty()
        popup.geometry(f"+{x}+{y}")

        frame = tk.Frame(popup, bg=COLORS['bg_panel'], padx=12, pady=10)
        frame.pack(fill='both')

        # IP
        tk.Label(frame, text="Camera IP:", font=FONTS['body'],
                 fg=COLORS['text_secondary'], bg=COLORS['bg_panel']).pack(anchor='w')
        ttk.Entry(frame, textvariable=self._ip_var, width=18).pack(anchor='w', pady=(2, 8))

        # Username
        tk.Label(frame, text="Username:", font=FONTS['body'],
                 fg=COLORS['text_secondary'], bg=COLORS['bg_panel']).pack(anchor='w')
        ttk.Entry(frame, textvariable=self._user_var, width=18).pack(anchor='w', pady=(2, 8))

        # Password
        tk.Label(frame, text="Password:", font=FONTS['body'],
                 fg=COLORS['text_secondary'], bg=COLORS['bg_panel']).pack(anchor='w')
        ttk.Entry(frame, textvariable=self._pass_var, width=18, show='*').pack(anchor='w', pady=(2, 8))

        # Quality
        tk.Label(frame, text="Stream Quality:", font=FONTS['body'],
                 fg=COLORS['text_secondary'], bg=COLORS['bg_panel']).pack(anchor='w')
        ttk.Combobox(
            frame, textvariable=self._quality_var,
            values=list(self.QUALITY_OPTIONS.keys()), width=14, state='readonly'
        ).pack(anchor='w', pady=(2, 8))

        # Display Size
        tk.Label(frame, text="Display Size:", font=FONTS['body'],
                 fg=COLORS['text_secondary'], bg=COLORS['bg_panel']).pack(anchor='w')
        size_combo = ttk.Combobox(
            frame, textvariable=self._size_var,
            values=list(self.SIZES.keys()), width=14, state='readonly'
        )
        size_combo.pack(anchor='w', pady=(2, 10))
        size_combo.bind('<<ComboboxSelected>>', self._on_size_change)

        # Close
        ModernButton(
            frame, text="Close", command=self._close_settings,
            width=60, height=28, bg_color=COLORS['btn_secondary'], font=FONTS['body']
        ).pack(anchor='e')

        self._settings_popup = popup
        popup.protocol("WM_DELETE_WINDOW", self._close_settings)

    def _close_settings(self):
        if self._settings_popup:
            try:
                self._settings_popup.destroy()
            except tk.TclError:
                pass
            self._settings_popup = None

    # === Connection ===

    def _build_rtsp_url(self) -> str:
        ip = self._ip_var.get().strip()
        user = self._user_var.get().strip()
        passwd = self._pass_var.get().strip()
        stream_path = self.QUALITY_OPTIONS.get(self._quality_var.get(), 'stream1')
        return f"rtsp://{user}:{passwd}@{ip}:{TAPO_RTSP_PORT}/{stream_path}"

    def _toggle_connection(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showwarning("No IP", "Please enter a camera IP address.")
            return

        rtsp_url = self._build_rtsp_url()
        self._status_var.set(f"Connecting to {ip}...")
        self._conn_led.set_state('connecting')

        self._stream_reader = RTSPStreamReader(
            rtsp_url,
            on_frame=self._on_frame_received,
            on_error=self._on_stream_error
        )
        self._stream_reader.start()

        self._connected = True
        self._connect_btn.set_text("Disconnect")
        self._connect_btn.configure_colors(bg_color=COLORS['btn_danger'])
        self._capture_btn.set_enabled(True)

    def _disconnect(self):
        if self._stream_reader:
            self._stream_reader.stop()
            self._stream_reader = None

        self._connected = False
        self._current_frame = None

        self._connect_btn.set_text("Connect")
        self._connect_btn.configure_colors(bg_color=COLORS['btn_primary'])
        self._conn_led.set_state('disconnected')
        self._capture_btn.set_enabled(False)
        self._save_btn.set_enabled(False)
        self._status_var.set("Disconnected")

        self._video_label.configure(image='', text="No Camera Connected")
        self._photo_image = None

    # === Frame Display ===

    def _on_frame_received(self, frame_data: bytes):
        self._current_frame = frame_data
        self.after(0, self._display_frame_data, frame_data)

    def _display_frame_data(self, frame_data: bytes):
        try:
            image = Image.open(io.BytesIO(frame_data))
            if self._display_size:
                image = image.resize(self._display_size, Image.Resampling.LANCZOS)

            self._photo_image = ImageTk.PhotoImage(image)
            self._video_label.configure(image=self._photo_image, text='')

            if self._connected:
                self._conn_led.set_state('connected')
                self._status_var.set(f"Connected - {image.size[0]}x{image.size[1]}")
        except Exception:
            pass

    def _on_stream_error(self, error: str):
        self.after(0, self._handle_stream_error, error)

    def _handle_stream_error(self, error: str):
        self._disconnect()
        self._status_var.set(f"Error: {error}")
        messagebox.showerror("TAPO Camera Error", error)

    # === Size ===

    def _on_size_change(self, event=None):
        size_name = self._size_var.get()
        self._display_size = self.SIZES.get(size_name)
        self._update_display_size()

    def _update_display_size(self):
        if self._display_size:
            w, h = self._display_size
            self._display_frame.configure(width=w, height=h)
            self._video_label.configure(width=w, height=h)
        else:
            self._display_frame.configure(width=320, height=240)

    # === Snapshot ===

    def _capture_snapshot(self):
        if self._current_frame:
            self._save_btn.set_enabled(True)
            self._status_var.set("Snapshot captured - click Save to save")

    def _save_snapshot(self):
        if not self._current_frame:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")],
            initialfile=f"tapo_snapshot_{int(time.time())}.jpg"
        )

        if filename:
            try:
                image = Image.open(io.BytesIO(self._current_frame))
                image.save(filename)
                self._status_var.set(f"Saved: {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save image: {e}")

    def destroy(self):
        self._close_settings()
        self._disconnect()
        super().destroy()
