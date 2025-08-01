#!/bin/bash
# Cleanup script to terminate all SVO frame extraction processes
# Usage: ./bash/cleanup.sh

echo "Cleaning up SVO frame extraction processes..."

# Kill all Python processes that are running the SVO frame extraction scripts
echo "Terminating Python processes running SVO frame extraction..."

# Kill processes running get_svo_frames.py
pkill -f "get_svo_frames.py" 2>/dev/null || echo "No get_svo_frames.py processes found"

# Kill processes running get_svo_frames_multithreaded.py
pkill -f "get_svo_frames_multithreaded.py" 2>/dev/null || echo "No get_svo_frames_multithreaded.py processes found"

# Kill any remaining Python processes that might be hanging
echo "Checking for any remaining Python processes..."
ps aux | grep -E "(get_svo_frames|pyzed)" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null

# Wait a moment for processes to terminate
sleep 2

# Check if any processes are still running
echo "Checking for remaining processes..."
REMAINING=$(ps aux | grep -E "(get_svo_frames|pyzed)" | grep -v grep | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Cleanup completed successfully. No remaining processes."
else
    echo "⚠️  Warning: $REMAINING processes may still be running:"
    ps aux | grep -E "(get_svo_frames|pyzed)" | grep -v grep
fi

echo "Cleanup script finished." 