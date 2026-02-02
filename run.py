#!/usr/bin/env python3
"""
Dart Delivery System - Application Entry Point

Run this script to start the GUI application.

Usage:
    python run.py

Alternative (module execution):
    python -m src
"""

import sys
import subprocess


def ensure_dependencies():
    """Check and install missing dependencies."""
    required = ['serial', 'PIL']
    packages = {'serial': 'pyserial', 'PIL': 'pillow'}
    missing = []

    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(packages[module])

    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)


ensure_dependencies()

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
