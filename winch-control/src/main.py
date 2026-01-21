"""
Main Application Module

Entry point for the Winch Control application.
"""

import sys
import tkinter as tk
from tkinter import messagebox

from .gui.main_window import MainWindow


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


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
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

        # Configure DPI awareness on Windows
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass  # Not on Windows or API not available

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
