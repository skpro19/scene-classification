#!/usr/bin/env bash
# Usage examples:
# ./bash/get_svo_frames.sh
# INPUT_DIR=custom/svo-files OUTPUT_DIR=custom/frames ./bash/get_svo_frames.sh
# ./bash/get_svo_frames.sh --input-dir custom/svo --overwrite
# OVERWRITE=1 ./bash/get_svo_frames.sh

set -euo pipefail

# Suppress ZED SDK logging
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

python3 "$PROJECT_ROOT/scripts/extract_svo_frames.py" \
    --input-dir "${INPUT_DIR:-data/svo-files}" \
    --output-dir "${OUTPUT_DIR:-data/svo-frames}" \
    --index-path "${INDEX_PATH:-index/processed-svos.json}" \
    ${OVERWRITE:+--overwrite} \
    "$@"