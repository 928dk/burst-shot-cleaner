#!/bin/bash

# Project: Burst Shot Cleaner
# Purpose: Manage virtual environment and launch application

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "=== Burst Shot Cleaner Launcher ==="

# Create virtual environment if it doesn't exist
# A dangling symlink is not a directory, so [ -d ] reports a broken venv as
# missing and `python3 -m venv` fails with EEXIST. Drop the dead link and probe
# the interpreter through it. (spec 152)
if [ -L "$VENV_DIR" ] && [ ! -d "$VENV_DIR" ]; then rm "$VENV_DIR"; fi
if ! [ -x "$VENV_DIR/bin/python3" ] || ! "$VENV_DIR/bin/python3" -c 'import sys' 2>/dev/null; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install/Update dependencies
echo "Verifying dependencies..."
pip install -q --upgrade pip
pip install -q -r "$PROJECT_DIR/requirements.txt"

# Launch application
echo "Launching Burst Shot Cleaner..."
python3 "$PROJECT_DIR/main.py"

# Deactivate venv on exit
deactivate
