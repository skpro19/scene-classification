#!/bin/bash

# SVO Service Startup Script
# This script starts the FastAPI SVO service

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to kill existing SVO service
kill_existing_service() {
    print_status "Checking for existing SVO service on port 8000..."
    
    # Find processes using port 8000
    PIDS=$(lsof -ti:8000 2>/dev/null || echo "")
    
    if [ -n "$PIDS" ]; then
        print_warning "Found existing service(s) on port 8000. Killing process(es): $PIDS"
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
        sleep 2  # Give time for the process to terminate
        
        # Verify the port is now free
        if lsof -ti:8000 >/dev/null 2>&1; then
            print_error "Failed to kill existing service on port 8000"
            exit 1
        else
            print_status "Successfully killed existing service"
        fi
    else
        print_status "No existing service found on port 8000"
    fi
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SVO_SERVICE_DIR="$PROJECT_ROOT/svo-service"

print_status "Starting SVO Service..."

# Kill any existing service first
kill_existing_service

# Check if we're in the right directory structure
if [ ! -d "$SVO_SERVICE_DIR" ]; then
    print_error "SVO service directory not found at: $SVO_SERVICE_DIR"
    print_error "Please ensure the script is run from the correct location"
    exit 1
fi

# Check if api.py exists
if [ ! -f "$SVO_SERVICE_DIR/api.py" ]; then
    print_error "api.py not found in $SVO_SERVICE_DIR"
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "$SVO_SERVICE_DIR/requirements.txt" ]; then
    print_error "requirements.txt not found in $SVO_SERVICE_DIR"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed or not in PATH"
    exit 1
fi

print_status "Checking dependencies..."

# Check if virtual environment exists, activate if it does
if [ -d "$SVO_SERVICE_DIR/venv" ]; then
    print_status "Activating virtual environment..."
    source "$SVO_SERVICE_DIR/venv/bin/activate"
else
    print_error "Virtual environment not found. Please run the setup first."
    exit 1
fi

# Check if ZED SDK is available
print_status "Checking ZED SDK availability..."
python3 -c "import pyzed.sl" 2>/dev/null || {
    print_warning "ZED SDK (pyzed) not found. SVO processing may not work."
    print_warning "Please install the ZED SDK and its Python wrapper."
}

# Change to the SVO service directory
cd "$SVO_SERVICE_DIR"

print_status "Starting SVO Service on http://localhost:8000"
print_status "API Documentation will be available at:"
print_status "  - Interactive docs: http://localhost:8000/docs"
print_status "  - ReDoc: http://localhost:8000/redoc"
print_status ""
print_status "Press Ctrl+C to stop the service"

# Start the service
python3 api.py 