#!/usr/bin/env bash
# Usage examples:
# ./bash/remove_hood.sh
# INPUT_DIR=custom/airslam-data OUTPUT_DIR=custom/airslam-no-hood ./bash/remove_hood.sh
# HOOD_HEIGHT=0.3 ./bash/remove_hood.sh
# ./bash/remove_hood.sh --input-dir custom/data --overwrite
# OVERWRITE=1 ./bash/remove_hood.sh

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

python3 "$PROJECT_ROOT/scripts/remove_hood.py" \
    --input-dir "${INPUT_DIR:-data/airslam-data}" \
    --output-dir "${OUTPUT_DIR:-data/airslam-no-hood}" \
    --index-path "${INDEX_PATH:-index/processed-hood-removal.json}" \
    --hood-height "${HOOD_HEIGHT:-0.25}" \
    ${OVERWRITE:+--overwrite} \
    "$@"
