#!/usr/bin/env bash
# Usage examples:
# ./bash/move_svo_files.sh
# SOURCE_DIR=custom/svo-frames TARGET_DIR=custom/svo-files ./bash/move_svo_files.sh
# ./bash/move_svo_files.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

python3 "$PROJECT_ROOT/scripts/move_svo_files.py" \
    --source "${SOURCE_DIR:-data/svo-frames}" \
    --target "${TARGET_DIR:-data/svo-files}" \
    ${DRY_RUN:+--dry-run} \
    "$@" 