#!/bin/bash
# Usage examples:
# ./bash/run_get_svos.sh
# S3_BUCKET=custom-bucket S3_PREFIX=custom/prefix PERCENTAGE=0.1 ./bash/run_get_svos.sh
# ./bash/run_get_svos.sh --bucket custom-bucket --prefix custom/prefix --percentage 0.15
# PERCENTAGE=0.2 ./bash/run_get_svos.sh

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

python3 scripts/download_svos.py \
    --bucket "${S3_BUCKET:-sg-new-data}" \
    --prefix "${S3_PREFIX:-dairy_farm/}" \
    --percentage "${PERCENTAGE:-0.2}" \
    "$@"
