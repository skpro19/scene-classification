#!/bin/bash

# This script installs dependencies and runs the SVO file downloader script.

# Exit on error
set -e

# Get the directory of this script
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# Project root is one level up from the 'bash' directory
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Activate the virtual environment
VENV_PATH="$PROJECT_ROOT/.venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH"
else
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Path to the requirements file and python script
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
PYTHON_SCRIPT="$PROJECT_ROOT/scripts/get_svos.py"

# Install dependencies
echo "Installing dependencies from $REQUIREMENTS_FILE..."
pip install -r "$REQUIREMENTS_FILE"

# Run the python script
echo "Running the SVO downloader script..."
python3 "$PYTHON_SCRIPT"

echo "Script finished."
