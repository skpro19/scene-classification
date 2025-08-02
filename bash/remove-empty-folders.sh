#!/bin/bash

# Script to recursively remove empty folders in data/svo-frames
# This script finds and removes all empty directories within the specified path

set -e  # Exit on any error

# Configuration
SVO_FRAMES_DIR="data/svo-frames"

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

# Check if the directory exists
if [ ! -d "$SVO_FRAMES_DIR" ]; then
    print_error "Directory '$SVO_FRAMES_DIR' does not exist!"
    exit 1
fi

print_status "Starting empty folder removal process..."
print_status "Target directory: $SVO_FRAMES_DIR"

# Count initial folders
initial_count=$(find "$SVO_FRAMES_DIR" -type d | wc -l)
print_status "Initial folder count: $initial_count"

# Find and remove empty directories
# -type d: only directories
# -empty: only empty directories
# -delete: remove them
# -print: print the names of removed directories

print_status "Removing empty folders..."

removed_count=0
while IFS= read -r -d '' dir; do
    if [ -d "$dir" ] && [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        print_status "Removing empty folder: $dir"
        rmdir "$dir"
        ((removed_count++))
    fi
done < <(find "$SVO_FRAMES_DIR" -type d -empty -print0)

# Count remaining folders
final_count=$(find "$SVO_FRAMES_DIR" -type d | wc -l)

print_status "Process completed!"
print_status "Removed $removed_count empty folders"
print_status "Final folder count: $final_count"

if [ $removed_count -gt 0 ]; then
    print_status "Empty folder cleanup completed successfully!"
else
    print_warning "No empty folders found to remove."
fi 