#!/bin/bash
# Usage examples:
# ./bash/run_get_svo_frames_multithreaded.sh
# INPUT_DIR=custom/svo-files OUTPUT_DIR=custom/frames NUM_THREADS=8 ./bash/run_get_svo_frames_multithreaded.sh
# ./bash/run_get_svo_frames_multithreaded.sh --input-dir custom/svo --num-threads 6 --overwrite
# OVERWRITE=1 ./bash/run_get_svo_frames_multithreaded.sh


# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != *".venv"* ]]; then
    echo "ERROR: Virtual environment (.venv) is not activated!"
    echo "Please activate the virtual environment first:"
    echo "  source .venv/bin/activate"
    exit 1
fi

python3 scripts/extract_svo_frames_multithreaded.py \
    --input-dir "${INPUT_DIR:-data/svo-files}" \
    --output-dir "${OUTPUT_DIR:-data/svo-frames}" \
    --index-path "${INDEX_PATH:-index/processed-svos.json}" \
    --num-threads "${NUM_THREADS:-10}" \
    ${OVERWRITE:+--overwrite} \
    "$@" 