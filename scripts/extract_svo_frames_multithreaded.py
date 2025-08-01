#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any



try:
    import cv2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – ci may not have cv2
    cv2 = None  # type: ignore

try:
    from tqdm import tqdm  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tqdm = None  # type: ignore

# Suppress ZED SDK logging at module level
import os
os.environ['ZED_LOG_LEVEL'] = 'ERROR'  # Only show errors, suppress INFO/WARNING
os.environ['ZED_SILENT_MODE'] = '1'  # Enable silent mode

# Import ZED SDK. Expect `pyzed` to be installed and expose the `sl` submodule.
try:
    import pyzed.sl as sl  # type: ignore
    # sl = pyzed.sl  # type: ignore[attr-defined]
except ModuleNotFoundError:
    print(
        "[ERROR] ZED SDK python module `pyzed` not found. Install it before running.",
        file=sys.stderr,
    )
    sys.exit(1)


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(description="Extract left images from SVO files (multithreaded)")
    p.add_argument(
        "--input-dir",
        default="data/svo-files",
        type=Path,
        help="Directory tree containing .svo files",
    )
    p.add_argument(
        "--output-dir",
        default="data/svo-frames",
        type=Path,
        help="Output directory where frames will be written",
    )
    p.add_argument(
        "--index-path",
        default="index/processed-svos.json",
        type=Path,
        help="JSON file that tracks already processed SVOs (paths are relative to input-dir)",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-extract frames even if the SVO already appears in the index",
    )
    p.add_argument(
        "--num-threads",
        type=int,
        default=4,
        help="Number of threads to use for concurrent processing",
    )
    return p.parse_args(argv)


def load_index(index_path: Path) -> set[str]:
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    return set(data)
        except json.JSONDecodeError:
            print(f"[WARN] Could not parse index file {index_path}. Starting fresh.")
    return set()


def save_index(index_path: Path, processed: set[str]):
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as fh:
        json.dump(sorted(processed), fh, indent=2)


def ensure_cv2():  # pragma: no cover
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) is required to save images but is not installed.")


class ThreadSafeIndex:
    """Thread-safe wrapper for the processed files index"""
    
    def __init__(self, index_path: Path, initial_processed: set[str]):
        self.index_path = index_path
        self.processed = initial_processed
        self.lock = threading.Lock()
    
    def add_processed(self, rel_str: str):
        with self.lock:
            self.processed.add(rel_str)
            # Save index after each successful processing
            save_index(self.index_path, self.processed)
    
    def is_processed(self, rel_str: str) -> bool:
        with self.lock:
            return rel_str in self.processed
    
    def get_processed_count(self) -> int:
        with self.lock:
            return len(self.processed)


def extract_frames_threaded(svo_file: Path, rel_path: Path, output_dir: Path, thread_id: int = 0):
    """Extract all left images from *svo_file* into *output_dir / rel_path without suffix*"""
    ensure_cv2()

    zed = sl.Camera()

    init_params = sl.InitParameters()
    # Disable depth for faster decode
    if hasattr(sl.DEPTH_MODE, "NONE"):
        init_params.depth_mode = sl.DEPTH_MODE.NONE  # type: ignore[attr-defined]
    # Point to SVO
    init_params.set_from_svo_file(str(svo_file))  # type: ignore[attr-defined]

    status = zed.open(init_params)
    if status != sl.ERROR_CODE.SUCCESS:  # type: ignore[attr-defined]
        raise RuntimeError(f"Failed to open {svo_file}: {status}")

    # Prepare output directory path (one folder per SVO file, sans extension)
    frame_root = (output_dir / rel_path).with_suffix("")  # drop .svo
    
    # Create output directory only after SVO is successfully opened
    frame_root.mkdir(parents=True, exist_ok=True)

    total_frames: int | None = None
    if hasattr(zed, "get_svo_number_of_frames"):
        total_frames = zed.get_svo_number_of_frames()

    mat = sl.Mat()
    runtime_params = sl.RuntimeParameters()

    # Create progress bar for current file (thread-specific position)
    if tqdm is not None:
        progress_it = tqdm(
            total=total_frames,
            unit="frame",
            desc=f"Thread-{thread_id}: {rel_path.name}",
            leave=False,
            position=thread_id + 1,  # Each thread gets its own line
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
    else:
        progress_it = None

    frame_id = 0
    saved_frame_id = 0
    try:
        while True:
            grab_status = zed.grab(runtime_params)
            if grab_status == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:  # type: ignore[attr-defined]
                break
            if grab_status != sl.ERROR_CODE.SUCCESS:  # type: ignore[attr-defined]
                continue  # skip errors – warn?

            # Only process every 10th frame (1/10 of all frames)
            if frame_id % 10 == 0:
                zed.retrieve_image(mat, sl.VIEW.LEFT)  # type: ignore[attr-defined]
                
                out_file = frame_root / f"{saved_frame_id:06d}.png"
                # Use ZED SDK's built-in save method instead of OpenCV
                save_status = mat.write(str(out_file))
                if save_status != sl.ERROR_CODE.SUCCESS:  # type: ignore[attr-defined]
                    print(f"Warning: Failed to save frame {saved_frame_id} for {rel_path}")
                else:
                    saved_frame_id += 1
                    if tqdm is not None:
                        progress_it.update(1)

            frame_id += 1
    finally:
        if tqdm is not None and hasattr(progress_it, "close"):
            progress_it.close()
        zed.close()

    return saved_frame_id


def process_svo_file(args: tuple[Path, Path, Path, int, ThreadSafeIndex, bool]) -> Dict[str, Any]:
    """Process a single SVO file - designed to be called by thread pool"""
    svo_file, rel_path, output_dir, thread_id, index_manager, overwrite = args
    rel_str = str(rel_path)
    
    # Check if already processed
    if index_manager.is_processed(rel_str) and not overwrite:
        return {
            'status': 'skipped',
            'rel_str': rel_str,
            'frames': 0,
            'duration': 0.0,
            'error': None
        }
    
    file_start_t = time.perf_counter()
    try:
        n_frames = extract_frames_threaded(svo_file, rel_path, output_dir, thread_id)
        file_duration = time.perf_counter() - file_start_t
        
        # Mark as processed
        index_manager.add_processed(rel_str)
        
        return {
            'status': 'success',
            'rel_str': rel_str,
            'frames': n_frames,
            'duration': file_duration,
            'error': None
        }
    except Exception as exc:
        file_duration = time.perf_counter() - file_start_t
        return {
            'status': 'error',
            'rel_str': rel_str,
            'frames': 0,
            'duration': file_duration,
            'error': str(exc)
        }


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    # Resolve paths (they may be relative)
    input_dir: Path = args.input_dir.expanduser().resolve()
    output_dir: Path = args.output_dir.expanduser().resolve()
    index_path: Path = args.index_path.expanduser().resolve()

    processed = load_index(index_path)
    index_manager = ThreadSafeIndex(index_path, processed)

    import random
    
    svo_files = list(input_dir.rglob("*.svo"))
    if not svo_files:
        print(f"No .svo files found in {input_dir}")
        return

    # Randomize the order of SVO files
    random.shuffle(svo_files)
    total = len(svo_files)

    # Filter out already processed files
    to_process = []
    for svo in svo_files:
        rel_path = svo.relative_to(input_dir)
        rel_str = str(rel_path)
        if rel_str not in processed or args.overwrite:
            to_process.append((svo, rel_path))
    
    if not to_process:
        print("All files have been processed. Use --overwrite to re-process.")
        return

    print(f"Found {len(to_process)} files to process out of {total} total files")
    print(f"Using {args.num_threads} threads")

    start_time = time.perf_counter()
    
    # Create global progress bar
    if tqdm is not None:
        global_pbar = tqdm(
            total=len(to_process),
            unit="file",
            desc="Global Progress",
            position=0,  # First line
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
    else:
        global_pbar = None
    
    # Prepare arguments for thread pool
    thread_args = []
    for i, (svo, rel_path) in enumerate(to_process):
        thread_args.append((svo, rel_path, output_dir, i % args.num_threads, index_manager, args.overwrite))
    
    # Process files using thread pool
    completed = 0
    successful = 0
    errors = 0
    skipped = 0
    
    with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
        # Submit all tasks
        future_to_args = {executor.submit(process_svo_file, args): args for args in thread_args}
        
        # Process completed tasks
        for future in as_completed(future_to_args):
            result = future.result()
            completed += 1
            
            if result['status'] == 'success':
                successful += 1
                fps = result['frames'] / result['duration'] if result['duration'] else 0
                if global_pbar is None:
                    print(f"[{completed}/{len(to_process)}] ✓ {result['rel_str']} - {result['frames']} frames in {result['duration']:.1f}s ({fps:.1f} fps)")
            elif result['status'] == 'error':
                errors += 1
                if global_pbar is None:
                    print(f"[{completed}/{len(to_process)}] ✗ {result['rel_str']} - ERROR: {result['error']}")
            elif result['status'] == 'skipped':
                skipped += 1
                if global_pbar is None:
                    print(f"[{completed}/{len(to_process)}] - {result['rel_str']} - Skipped (already processed)")
            
            # Update global progress bar
            if global_pbar is not None:
                global_pbar.update(1)
                
                # Update description with current stats
                remaining = len(to_process) - completed
                
                global_pbar.set_description(
                    f"Global: {completed}/{len(to_process)} - {remaining} remaining "
                    f"(✓{successful} ✗{errors} -{skipped})"
                )

    # Clean up global progress bar
    if global_pbar is not None:
        global_pbar.close()

    total_duration = time.perf_counter() - start_time
    print(f"\nProcessing completed in {total_duration:.1f}s")
    print(f"Results: {successful} successful, {errors} errors, {skipped} skipped")
    
    pending = total - index_manager.get_processed_count()
    print(f"Total pending SVO files: {pending}")


if __name__ == "__main__":
    main() 