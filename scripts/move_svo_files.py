#!/usr/bin/env python3
"""
Script to recursively move .svo files from data/svo-frames to data/svo-files
while preserving their relative directory structure.
"""

import os
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple


def find_svo_files(source_dir: Path) -> List[Tuple[Path, Path]]:
    """
    Find all .svo files in the source directory and return their current and target paths.
    
    Args:
        source_dir: Path to the source directory (data/svo-frames)
        
    Returns:
        List of tuples containing (current_path, target_path)
    """
    svo_files = []
    
    for root, dirs, files in os.walk(source_dir):
        root_path = Path(root)
        
        for file in files:
            if file.endswith('.svo'):
                current_path = root_path / file
                
                # Calculate relative path from source_dir
                relative_path = current_path.relative_to(source_dir)
                
                # Create target path in data/svo-files
                target_path = Path('data/svo-files') / relative_path
                
                svo_files.append((current_path, target_path))
    
    return svo_files


def move_svo_files(source_dir: Path, target_dir: Path, dry_run: bool = False) -> None:
    """
    Move all .svo files from source_dir to target_dir while preserving structure.
    
    Args:
        source_dir: Source directory (data/svo-frames)
        target_dir: Target directory (data/svo-files)
        dry_run: If True, only print what would be moved without actually moving
    """
    if not source_dir.exists():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return
    
    # Create target directory if it doesn't exist
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all .svo files
    svo_files = find_svo_files(source_dir)
    
    if not svo_files:
        print("No .svo files found in the source directory.")
        return
    
    print(f"Found {len(svo_files)} .svo files to move.")
    
    moved_count = 0
    error_count = 0
    
    for current_path, target_path in svo_files:
        try:
            # Create target directory if it doesn't exist
            if not dry_run:
                target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if dry_run:
                print(f"Would move: {current_path} -> {target_path}")
            else:
                # Move the file
                shutil.move(str(current_path), str(target_path))
                print(f"Moved: {current_path} -> {target_path}")
                moved_count += 1
                
        except Exception as e:
            print(f"Error moving {current_path}: {e}")
            error_count += 1
    
    if dry_run:
        print(f"\nDry run completed. Would move {len(svo_files)} files.")
    else:
        print(f"\nOperation completed:")
        print(f"  - Successfully moved: {moved_count} files")
        print(f"  - Errors: {error_count} files")


def main():
    parser = argparse.ArgumentParser(
        description="Move .svo files from data/svo-frames to data/svo-files while preserving structure"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without actually moving files"
    )
    parser.add_argument(
        "--source",
        default="data/svo-frames",
        help="Source directory (default: data/svo-frames)"
    )
    parser.add_argument(
        "--target",
        default="data/svo-files",
        help="Target directory (default: data/svo-files)"
    )
    
    args = parser.parse_args()
    
    source_dir = Path(args.source)
    target_dir = Path(args.target)
    
    print(f"Moving .svo files from '{source_dir}' to '{target_dir}'")
    if args.dry_run:
        print("DRY RUN MODE - No files will be actually moved")
    print("-" * 50)
    
    move_svo_files(source_dir, target_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main() 