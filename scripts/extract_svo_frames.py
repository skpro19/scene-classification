#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


import cv2
from tqdm import tqdm
import pyzed.sl as sl

from logger import LOGGER



def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(description="Extract left images from SVO files")
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
        "--resolution",
        default="640,480",
        help="Image resolution as 'width,height' (e.g., '640,480', '1920,1080')",
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
            LOGGER.warning(f"Could not parse index file {index_path}. Starting fresh.")
    return set()


def save_index(index_path: Path, processed: set[str]):
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as fh:
        json.dump(sorted(processed), fh, indent=2)


def ensure_cv2():  # pragma: no cover
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) is required to save images but is not installed.")


def extract_frames(svo_file: Path, rel_path: Path, output_dir: Path, resolution: str = "640,480"):
    """Extract all left images from *svo_file* into *output_dir / rel_path without suffix*"""
    ensure_cv2()

    LOGGER.info(f"Extracting frames from {svo_file}")
    
    zed = sl.Camera()

    init_params = sl.InitParameters(sdk_verbose=False)
    
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
        LOGGER.info(f"Total frames: {total_frames}")
    else:
        LOGGER.warning("Could not get total number of frames")
        total_frames = None


    mat = sl.Mat()
    runtime_params = sl.RuntimeParameters()

    # Create progress bar for current file
    if tqdm is not None:
        progress_it = tqdm(
            total=total_frames,
            unit="frame",
            desc=f"  {rel_path.name}",
            leave=False,
            position=1,  # Second line
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
    else:
        progress_it = None

    frame_id = 0
    saved_frame_id = 0
    try:
        while True:
            # LOGGER.info(f"Grabbing frame {frame_id}")
            grab_status = zed.grab(runtime_params)
            if grab_status == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:  # type: ignore[attr-defined]
                break
            if grab_status != sl.ERROR_CODE.SUCCESS:  # type: ignore[attr-defined]
                continue  # skip errors – warn?

            # Only process every 10th frame (1/10 of all frames)
            if frame_id % 10 == 0:
                # LOGGER.info(f"Retrieving frame {frame_id}")
                # Parse resolution from string (e.g., "640,480")
                width, height = map(int, resolution.split(","))
                custom_res = sl.Resolution(width, height)
                zed.retrieve_image(mat, sl.VIEW.LEFT, resolution=custom_res)  # type: ignore[attr-defined]
                
                out_file = frame_root / f"{saved_frame_id:06d}.png"
                # Use ZED SDK's built-in save method instead of OpenCV
                save_status = mat.write(str(out_file))
                if save_status != sl.ERROR_CODE.SUCCESS:  # type: ignore[attr-defined]
                    LOGGER.warning(f"Failed to save frame {saved_frame_id} for {rel_path}")
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


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    # Resolve paths (they may be relative)
    input_dir: Path = args.input_dir.expanduser().resolve()
    output_dir: Path = args.output_dir.expanduser().resolve()
    index_path: Path = args.index_path.expanduser().resolve()

    processed = load_index(index_path)

    import random
    
    svo_files = list(input_dir.rglob("*.svo"))
    if not svo_files:
        LOGGER.warning(f"No .svo files found in {input_dir}")
        return

    # Randomize the order of SVO files
    random.shuffle(svo_files)
    total = len(svo_files)

    start_time = time.perf_counter()
    
    # Create global progress bar
    if tqdm is not None:
        global_pbar = tqdm(
            total=total,
            unit="file",
            desc="Global Progress",
            position=0,  # First line
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
    else:
        global_pbar = None
    
    for i, svo in enumerate(svo_files, 1):
        rel_path = svo.relative_to(input_dir)
        rel_str = str(rel_path)

        if global_pbar is not None:
            global_pbar.set_description(f"Global: {i}/{total}")
        else:
            LOGGER.info(f"[{i}/{total}] Processing {rel_str}")


        found = rel_str in processed

        if not found:
            LOGGER.warning(f"{i} => {rel_str} => {found}")

        # if found and not args.overwrite:
        #     if global_pbar is None:
        #         LOGGER.info("   • Skipped – already processed")
        #     continue

        if found and not args.overwrite:
            continue

        file_start_t = time.perf_counter()
        try:
            n_frames = extract_frames(svo, rel_path, output_dir, args.resolution)
        except Exception as exc:
            if global_pbar is None:
                LOGGER.error(f"Failed to process {rel_str}: {exc}")
            continue
        file_duration = time.perf_counter() - file_start_t
        fps = n_frames / file_duration if file_duration else 0
        
        if global_pbar is None:
            LOGGER.info(f"   • Done. Extracted {n_frames} frames in {file_duration:.1f}s ({fps:.1f} fps)")

        processed.add(rel_str)
        save_index(index_path, processed)
        
        # Update global progress bar
        if global_pbar is not None:
            global_pbar.update(1)

    # Clean up global progress bar
    if global_pbar is not None:
        global_pbar.close()

    pending = total - len(processed)
    LOGGER.info(f"All done. Pending SVO files: {pending}")


if __name__ == "__main__":
    main()