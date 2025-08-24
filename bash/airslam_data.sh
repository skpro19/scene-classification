#!/usr/bin/env bash
# Usage examples:
# ./bash/airslam_data.sh
# INPUT_DIR=custom/svo-files OUTPUT_DIR=custom/frames ./bash/airslam_data.sh
# RESOLUTION=1920,1080 ./bash/airslam_data.sh
# ./bash/airslam_data.sh --input-dir custom/svo --overwrite
# OVERWRITE=1 ./bash/airslam_data.sh

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

python3 "$PROJECT_ROOT/scripts/airslam_data.py" \
    --input-dir "${INPUT_DIR:-data/svo-files}" \
    --output-dir "${OUTPUT_DIR:-data/airslam-data}" \
    --index-path "${INDEX_PATH:-index/airslam-data.json}" \
    --resolution "${RESOLUTION:-640,480}" \
    ${OVERWRITE:+--overwrite} \
    "$@"
