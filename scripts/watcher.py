#!/usr/bin/env python3
"""
Monitors the discrepancy between downloaded and processed SVO files, and
triggers the frame extraction script when a threshold is met.

This script is designed to run continuously as a lightweight service.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from logger import LOGGER

# --- Configuration ---
# Default values
DEFAULT_POLL_INTERVAL_SECONDS = 300
DEFAULT_SVO_THRESHOLD = 5
# The command to execute
PROCESSING_SCRIPT = Path(__file__).parent.parent / "bash/get_svo_frames.sh"
# Script name to check if it's already running
PROCESS_NAME_TO_CHECK = "extract_svo_frames"

try:
    import psutil
except ImportError:
    LOGGER.error("psutil is not installed. Please install it with: pip install psutil")
    exit(1)


def parse_args(argv: list[str] | None = None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Monitor SVO files and trigger processing when threshold is met")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help=f"Polling interval in seconds (default: {DEFAULT_POLL_INTERVAL_SECONDS})"
    )
    parser.add_argument(
        "--svo-threshold",
        type=int,
        default=DEFAULT_SVO_THRESHOLD,
        help=f"Minimum number of unprocessed SVOs to trigger processing (default: {DEFAULT_SVO_THRESHOLD})"
    )
    return parser.parse_args(argv)


def get_project_root() -> Path:
    """Gets the project root directory."""
    return Path(__file__).parent.parent.resolve()


def is_process_running(name: str) -> bool:
    """Check if a process with a given name is currently running."""
    for proc in psutil.process_iter(["name", "cmdline"]):
        # Check process name and command line for the script name
        if name in proc.info.get("name", "") or any(
            name in part for part in proc.info.get("cmdline", [])
        ):
            LOGGER.info(f"Process '{name}' is already running (PID: {proc.pid}). Skipping this cycle.")
            return True
    return False


def get_unprocessed_count(root: Path) -> int:
    """
    Calculates the number of SVOs that are downloaded but not yet processed.
    """
    downloaded_path = root / "index/downloaded-svos.json"
    processed_path = root / "index/processed-svos.json"

    try:
        with downloaded_path.open("r", encoding="utf-8") as f:
            downloaded_urls = json.load(f)
        # Extract the relative path from the S3 URL
        # e.g., s3://sg-new-data/dairy_farm/path/to/file.svo -> path/to/file.svo
        s3_prefix = "s3://sg-new-data/dairy_farm/"
        downloaded_set = {url.removeprefix(s3_prefix) for url in downloaded_urls}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        LOGGER.warning(f"Could not read/parse {downloaded_path}: {e}")
        return 0

    try:
        with processed_path.open("r", encoding="utf-8") as f:
            processed_set = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # If the processed file doesn't exist, assume nothing is processed
        LOGGER.warning(f"Could not read/parse {processed_path}: {e}. Assuming no files processed.")
        processed_set = set()

    unprocessed_count = len(downloaded_set - processed_set)
    LOGGER.info(f"Found {unprocessed_count} unprocessed SVO files.")
    return unprocessed_count


def run_processing_script():
    """Executes the SVO frame extraction script."""
    if not PROCESSING_SCRIPT.exists():
        LOGGER.error(f"Processing script not found at: {PROCESSING_SCRIPT}")
        return

    LOGGER.info("Threshold met. Starting frame extraction process...")
    try:
        # We run the script and wait for it to complete.
        # The output (stdout/stderr) will be printed to the watcher's console.
        result = subprocess.run(
            [str(PROCESSING_SCRIPT)],
            check=True,
            text=True,
            capture_output=True,
        )
        LOGGER.info("Processing script finished successfully.")
        LOGGER.debug("Script stdout:\n%s", result.stdout)
    except subprocess.CalledProcessError as e:
        LOGGER.error("Processing script failed with exit code %d.", e.returncode)
        LOGGER.error("Stderr:\n%s", e.stderr)
        LOGGER.error("Stdout:\n%s", e.stdout)
    except Exception as e:
        LOGGER.error(f"An unexpected error occurred while running the script: {e}")


def main():
    """Main polling loop."""
    args = parse_args()
    project_root = get_project_root()
    
    LOGGER.info(f"Watcher service started with poll interval: {args.poll_interval}s, threshold: {args.svo_threshold}")
    LOGGER.info("Press Ctrl+C to exit.")

    while True:
        try:
            if is_process_running(PROCESS_NAME_TO_CHECK):
                time.sleep(args.poll_interval)
                continue

            unprocessed_count = get_unprocessed_count(project_root)

            if unprocessed_count >= args.svo_threshold:
                run_processing_script()

        except Exception as e:
            LOGGER.error(f"An error occurred in the watcher loop: {e}", exc_info=True)

        LOGGER.info(f"Sleeping for {args.poll_interval / 60:.0f} minutes...")
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
