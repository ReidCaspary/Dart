"""
Main Application Module

Entry point for the Winch Control application.
"""

import sys
import tkinter as tk
from tkinter import messagebox

from .gui.main_window import MainWindow
from .gui.theme import configure_modern_theme


def check_dependencies() -> bool:
    """
    Check that required dependencies are installed.

    Returns:
        True if all dependencies are available
    """
    try:
        import serial
        import serial.tools.list_ports
        return True
    except ImportError as e:
        return False


def configure_dpi_awareness():
    """
    Configure DPI awareness for Windows.
    Must be called BEFORE creating any Tk windows.
    """
    try:
        from ctypes import windll
        # Try per-monitor DPI awareness v2 (Windows 10 1703+)
        try:
            windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            # Fall back to system DPI awareness
            windll.user32.SetProcessDPIAware()
    except Exception:
        pass  # Not on Windows or API not available


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Configure DPI awareness BEFORE creating any Tk windows
    configure_dpi_awareness()

    # Check dependencies
    if not check_dependencies():
        # Try to show GUI error if possible
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Missing Dependencies",
                "Required package 'pyserial' is not installed.\n\n"
                "Please run: pip install pyserial"
            )
            root.destroy()
        except Exception:
            print("Error: Required package 'pyserial' is not installed.")
            print("Please run: pip install pyserial")
        return 1

    # Create and run application
    try:
        root = tk.Tk()

        # Enable Tk scaling based on DPI
        try:
            # Get the DPI scaling factor from Windows
            from ctypes import windll
            dpi = windll.user32.GetDpiForWindow(root.winfo_id())
            if dpi == 0:
                dpi = windll.user32.GetDpiForSystem()
            scaling_factor = dpi / 96.0
            root.tk.call('tk', 'scaling', scaling_factor)
        except Exception:
            pass

        # Apply modern dark theme
        configure_modern_theme(root)

        app = MainWindow(root)
        app.run()
        return 0

    except Exception as e:
        # Show error dialog
        try:
            messagebox.showerror("Application Error", f"An error occurred:\n{e}")
        except Exception:
            print(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
