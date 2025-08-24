#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from logger import LOGGER


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(description="Remove hood from front-facing camera images")
    p.add_argument(
        "--input-dir",
        default="data/airslam-data",
        type=Path,
        help="Directory containing front- folders with images",
    )
    p.add_argument(
        "--output-dir",
        default="data/airslam-no-hood",
        type=Path,
        help="Output directory for processed images",
    )
    p.add_argument(
        "--index-path",
        default="index/processed-hood-removal.json",
        type=Path,
        help="JSON file that tracks already processed front folders",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-process images even if the folder already appears in the index",
    )
    p.add_argument(
        "--hood-height",
        default=0.25,
        type=float,
        help="Fraction of image height to mask from bottom (default: 0.25)",
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


def remove_hood_from_image(image_path: Path, output_path: Path, hood_height_fraction: float = 0.25):
    """Remove hood from a single image by cropping the bottom portion."""
    # Read the image
    image = cv2.imread(str(image_path))
    if image is None:
        LOGGER.error(f"Failed to read image: {image_path}")
        return False

    height, width = image.shape[:2]

    # Calculate the hood region (bottom portion of the image)
    hood_height = int(height * hood_height_fraction)
    crop_height = height - hood_height

    # Crop the image to remove the hood area
    cropped_image = image[:crop_height, :]

    # Optionally resize back to original height to maintain aspect ratio
    # cropped_image = cv2.resize(cropped_image, (width, height), interpolation=cv2.INTER_CUBIC)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the processed image
    success = cv2.imwrite(str(output_path), cropped_image)
    if not success:
        LOGGER.error(f"Failed to save processed image: {output_path}")
        return False

    return True


def process_front_folder(front_folder: Path, output_dir: Path, hood_height_fraction: float = 0.25, base_input_dir: Path = None):
    """Process all images in a front- folder."""
    LOGGER.info(f"Processing folder: {front_folder}")

    # Use the consistent base_input_dir passed from main() function
    if base_input_dir:
        try:
            rel_path = front_folder.relative_to(base_input_dir)
        except ValueError:
            # Fallback: use just the folder name
            rel_path = front_folder.name
    else:
        # Fallback to the old logic if base_input_dir not provided
        try:
            # Get the path relative to the airslam-data directory
            rel_path = front_folder.relative_to(front_folder.parent.parent.parent)
        except ValueError:
            # Fallback: use just the folder name
            rel_path = front_folder.name

    # Create output path maintaining the same structure
    output_folder = output_dir / rel_path

    # Find all PNG images in the cam0/data directory
    cam0_data_dir = front_folder / "cam0" / "data"
    if not cam0_data_dir.exists():
        LOGGER.warning(f"No cam0/data directory found in {front_folder}")
        return False

    image_files = list(cam0_data_dir.glob("*.png"))
    if not image_files:
        LOGGER.warning(f"No PNG images found in {cam0_data_dir}")
        return False

    LOGGER.info(f"Found {len(image_files)} images to process")

    success_count = 0
    for image_file in tqdm(image_files, desc=f"Processing {front_folder.name}"):
        # Create corresponding output path
        output_image_path = output_folder / "cam0" / "data" / image_file.name

        # Skip if output already exists and we're not overwriting
        if output_image_path.exists():
            continue

        if remove_hood_from_image(image_file, output_image_path, hood_height_fraction):
            success_count += 1

    # Also create cam1 directory structure if it exists in the input (for consistency)
    cam1_data_dir = front_folder / "cam1" / "data"
    if cam1_data_dir.exists():
        # Create the cam1 directory structure in output
        output_cam1_dir = output_folder / "cam1" / "data"
        output_cam1_dir.mkdir(parents=True, exist_ok=True)

        # Copy cam1 images as-is (no processing needed for right camera)
        cam1_images = list(cam1_data_dir.glob("*.png"))
        for cam1_image in cam1_images:
            output_cam1_path = output_cam1_dir / cam1_image.name
            if not output_cam1_path.exists():
                import shutil
                shutil.copy2(str(cam1_image), str(output_cam1_path))

        if cam1_images:
            LOGGER.info(f"Copied {len(cam1_images)} cam1 images as-is")

    LOGGER.info(f"Successfully processed {success_count}/{len(image_files)} images")
    return success_count > 0


def find_front_folders(input_dir: Path) -> list[Path]:
    """Find all folders that start with 'front-' in the input directory tree."""
    front_folders = []

    for folder in input_dir.rglob("*"):
        if folder.is_dir() and folder.name.startswith("front_"):
            front_folders.append(folder)

    return sorted(front_folders)


def main():
    args = parse_args()

    # Ensure input directory exists
    if not args.input_dir.exists():
        LOGGER.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    # Load processing index
    processed_folders = load_index(args.index_path) if not args.overwrite else set()

    # Find all front- folders
    front_folders = find_front_folders(args.input_dir)
    LOGGER.info(f"Found {len(front_folders)} front- folders to process")

    if not front_folders:
        LOGGER.warning("No front- folders found in the input directory")
        return

    # Determine the base directory for consistent path calculation
    # This should be the airslam-data directory or equivalent
    base_input_dir = args.input_dir
    if "airslam-data" in str(args.input_dir):
        # Find the airslam-data directory to get consistent paths
        parts = args.input_dir.parts
        for i, part in enumerate(parts):
            if part == "airslam-data":
                base_input_dir = Path(*parts[:i+1])
                break

    # Process each front folder
    for front_folder in front_folders:
        # Get relative path for index tracking (consistent with airslam-data.json format)
        try:
            rel_path = front_folder.relative_to(base_input_dir)
            rel_path_str = str(rel_path)
        except ValueError:
            # Fallback: use path relative to input_dir
            try:
                rel_path = front_folder.relative_to(args.input_dir)
                rel_path_str = str(rel_path)
            except ValueError:
                rel_path_str = front_folder.name

        # Skip if already processed
        if rel_path_str in processed_folders:
            LOGGER.info(f"Skipping already processed folder: {rel_path_str}")
            continue

        # Process the folder
        if process_front_folder(front_folder, args.output_dir, args.hood_height, base_input_dir):
            # Update index immediately after successful processing (like airslam_data.py)
            processed_folders.add(rel_path_str)
            save_index(args.index_path, processed_folders)
            LOGGER.info(f"Updated index with processed folder: {rel_path_str}")

    LOGGER.info("Processing complete!")


if __name__ == "__main__":
    main()
