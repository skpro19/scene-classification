import boto3
import os
import math
import json
import argparse
from collections import defaultdict
from tqdm import tqdm
from typing import Set, List, Dict, Any
from logger import LOGGER

def load_downloaded_index() -> Set[str]:
    """
    Load the list of already downloaded files from the JSON index.
    
    Returns:
        set: Set of S3 URIs that have been downloaded
    """
    index_file = "index/downloaded-svos.json"
    if not os.path.exists(index_file):
        return set()
    
    try:
        with open(index_file, 'r') as f:
            downloaded_files = json.load(f)
        return set(downloaded_files)
    except Exception as e:
        LOGGER.error(f"Error loading downloaded index: {e}")
        return set()

def update_downloaded_index(s3_uri: str) -> None:
    """
    Add a newly downloaded file to the downloaded index.
    
    Args:
        s3_uri (str): The S3 URI of the file that was downloaded
    """
    index_file = "index/downloaded-svos.json"
    
    # Load existing index
    try:
        if os.path.exists(index_file):
            with open(index_file, 'r') as f:
                downloaded_files = json.load(f)
        else:
            downloaded_files = []
    except Exception as e:
        LOGGER.error(f"Error loading downloaded index for update: {e}")
        downloaded_files = []
    
    # Add the new file if it's not already in the list
    if s3_uri not in downloaded_files:
        downloaded_files.append(s3_uri)
        
        # Ensure the index directory exists
        os.makedirs(os.path.dirname(index_file), exist_ok=True)
        
        # Write back to file
        try:
            with open(index_file, 'w') as f:
                json.dump(downloaded_files, f, indent=2)
        except Exception as e:
            LOGGER.error(f"Error updating downloaded index: {e}")

def is_file_downloaded(s3_key: str, downloaded_files: Set[str], bucket_name: str) -> bool:
    """
    Check if a file has already been downloaded by comparing its S3 URI.
    
    Args:
        s3_key (str): The S3 key of the file to check
        downloaded_files (set): Set of S3 URIs that have been downloaded
        bucket_name (str): The S3 bucket name
        
    Returns:
        bool: True if the file has been downloaded, False otherwise
    """
    s3_uri = f"s3://{bucket_name}/{s3_key}"
    return s3_uri in downloaded_files

def get_svo_files(bucket_name: str, prefix: str, download_percentage: float = 0.05) -> None:
    """
    Downloads a specified percentage of .svo files from each leaf-folder in an S3 path.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix (folder path) to search within.
        download_percentage (float): Percentage of files to download (0.0 to 1.0). Default is 0.05 (5%).
    """
    s3_client = boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")

    all_folders: Set[str] = set()
    parent_folders: Set[str] = set()
    svo_files: Dict[str, List[str]] = defaultdict(list)

    # Ensure prefix ends with a slash
    if not prefix.endswith('/'):
        prefix += '/'

    LOGGER.info(f"Finding leaf folders and .svo files in s3://{bucket_name}/{prefix}...")

    # First pass: identify all folders and SVO files
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if "Contents" not in page:
            continue
        for obj in page["Contents"]:
            key = obj["Key"]
            folder = os.path.dirname(key)
            
            if folder != prefix.strip('/'):
                all_folders.add(folder)

            relative_path = os.path.relpath(folder, prefix)
            if '/' in relative_path:
                # This logic finds parent folders by checking if a folder's path contains subdirectories.
                # The first part of the relative path is the top-level folder within the prefix.
                parent = os.path.join(prefix.strip('/'), relative_path.split('/')[0])
                parent_folders.add(parent)

            if key.endswith(".svo"):
                svo_files[folder].append(key)

    leaf_folders: List[str] = sorted(list(all_folders - parent_folders))

    if not leaf_folders:
        LOGGER.warning("No leaf folders found.")
        return

    LOGGER.info(f"Found {len(leaf_folders)} leaf folders.")

    # Load already downloaded files
    downloaded_files: Set[str] = load_downloaded_index()
    LOGGER.info(f"Found {len(downloaded_files)} already downloaded files in index.")
    LOGGER.info("--------------------------------")


    # Second pass: download files from leaf folders
    for folder in leaf_folders:
        files_to_download: List[str] = svo_files[folder]
        if not files_to_download:
            LOGGER.info(f"\nNo .svo files found in {folder}. Skipping.")
            continue

        # Filter out already downloaded files
        files_to_download = [f for f in files_to_download if not is_file_downloaded(f, downloaded_files, bucket_name)]
        LOGGER.info(f"--------------------------------")
        LOGGER.info(f"Found {len(files_to_download)} files to download from {folder}.")
        LOGGER.info(f"--------------------------------\n")

        if not files_to_download:
            LOGGER.info(f"\nAll files in {folder} already downloaded. Skipping.")
            continue

        # Calculate percentage of files to download, rounding up
        num_to_download: int = math.ceil(len(files_to_download) * download_percentage)
        
        # Get the relative path for the local directory
        relative_folder_path: str = os.path.relpath(folder, prefix)
        local_dir: str = os.path.join("data", "svo-frames", relative_folder_path)
        os.makedirs(local_dir, exist_ok=True)

        LOGGER.info(f"\nDownloading {num_to_download} of {len(files_to_download)} .svo files from '{folder}' to '{local_dir}'...")

        # Select the first percentage of files
        download_list: List[str] = files_to_download[:num_to_download]

        with tqdm(total=len(download_list), unit="file", desc=f"Folder {relative_folder_path}") as pbar:
            for s3_key in download_list:
                local_file_path: str = os.path.join(local_dir, os.path.basename(s3_key))
                try:
                    s3_client.download_file(bucket_name, s3_key, local_file_path)
                    # Update the downloaded index after successful download
                    s3_uri: str = f"s3://{bucket_name}/{s3_key}"
                    update_downloaded_index(s3_uri)
                except Exception as e:
                    LOGGER.error(f"Error downloading {s3_key}: {e}")
                pbar.update(1)

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Download SVO files from S3 bucket with configurable parameters"
    )
    parser.add_argument(
        "--bucket", 
        "-b",
        type=str,
        default="sg-new-data",
        help="S3 bucket name (default: sg-new-data)"
    )
    parser.add_argument(
        "--prefix", 
        "-p",
        type=str,
        default="dairy_farm/",
        help="S3 prefix/path to search in (default: dairy_farm/)"
    )
    parser.add_argument(
        "--percentage", 
        "-%",
        type=float,
        default=0.05,
        help="Percentage of files to download (0.0 to 1.0, default: 0.05 for 5%%)"
    )
    
    return parser.parse_args()

def main() -> None:
    """Main function to execute the SVO file download process."""
    args = parse_arguments()
    
    # Validate percentage argument
    if not 0.0 <= args.percentage <= 1.0:
        LOGGER.error("Error: Percentage must be between 0.0 and 1.0")
        return
    
    LOGGER.info(f"Starting download with parameters:")
    LOGGER.info(f"  Bucket: {args.bucket}")
    LOGGER.info(f"  Prefix: {args.prefix}")
    LOGGER.info(f"  Download percentage: {args.percentage * 100:.1f}%")
    LOGGER.info("-" * 50)
    
    get_svo_files(args.bucket, args.prefix, args.percentage)

if __name__ == "__main__":
    main()
