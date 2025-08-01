#!/bin/bash
# Usage examples:
# ./bash/run_watcher.sh
# POLL_INTERVAL=600 SVO_THRESHOLD=10 ./bash/run_watcher.sh
# ./bash/run_watcher.sh --help
# OVERWRITE=1 ./bash/run_watcher.sh

# Suppress ZED SDK logging (in case the watcher triggers scripts that use ZED)
export ZED_LOG_LEVEL=ERROR
export ZED_SILENT_MODE=1

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != *".venv"* ]]; then
    echo "ERROR: Virtual environment (.venv) is not activated!"
    echo "Please activate the virtual environment first:"
    echo "  source .venv/bin/activate"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Generate log filename with timestamp
LOG_FILE="$PROJECT_ROOT/logs/watcher_$(date +%Y%m%d_%H%M%S).log"

python3 "$PROJECT_ROOT/scripts/watcher.py" \
    --poll-interval "${POLL_INTERVAL:-300}" \
    --svo-threshold "${SVO_THRESHOLD:-5}" \
    "$@" 2>&1 | tee "$LOG_FILE" 