#!/usr/bin/env python3
"""
Winch Control Application Entry Point

Run this script to start the GUI application.
"""

import sys
import os
import subprocess

# Add winch-control to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'winch-control'))

# Check and install missing dependencies
def ensure_dependencies():
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
