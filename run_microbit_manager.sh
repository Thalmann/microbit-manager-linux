#!/bin/bash
"""
Microbit Manager Runner
Convenient wrapper script to run the microbit manager with proper privileges
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/microbit_manager.py"

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: microbit_manager.py not found in $SCRIPT_DIR"
    exit 1
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Starting Microbit Manager..."
    python3 "$PYTHON_SCRIPT"
else
    echo "Microbit Manager requires sudo privileges to mount/unmount devices."
    echo "Starting with sudo..."
    echo ""
    sudo python3 "$PYTHON_SCRIPT"
fi