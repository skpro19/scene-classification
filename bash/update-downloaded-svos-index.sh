#!/bin/bash
# Usage examples:
# ./bash/update-downloaded-svos-index.sh
# INDEX_FILE=custom/index.json SVO_FILES_DIR=custom/svo-files ./bash/update-downloaded-svos-index.sh
# ./bash/update-downloaded-svos-index.sh --index-file custom/index.json --s3-uri-prefix s3://my-bucket/prefix

python3 scripts/update-downloaded-svos-index.py \
    --index-file "${INDEX_FILE:-index/downloaded-svos.json}" \
    --svo-files-dir "${SVO_FILES_DIR:-data/svo-files}" \
    --s3-uri-prefix "${S3_URI_PREFIX:-s3://sg-new-data/dairy_farm}" \
    "$@" 