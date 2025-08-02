#!/usr/bin/env bash
# Usage examples:
# ./bash/extract_svo_frames.sh
# INPUT_DIR=custom/svo-files OUTPUT_DIR=custom/frames ./bash/extract_svo_frames.sh
# RESOLUTION=1920,1080 ./bash/extract_svo_frames.sh
# ./bash/extract_svo_frames.sh --input-dir custom/svo --overwrite
# OVERWRITE=1 ./bash/extract_svo_frames.sh

set -euo pipefail

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
    --resolution "${RESOLUTION:-640,480}" \
    ${OVERWRITE:+--overwrite} \
    "$@"