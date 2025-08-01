import boto3
import os
import math
from collections import defaultdict
from tqdm import tqdm

def get_svo_files(bucket_name, prefix):
    """
    Downloads 5% of .svo files from each leaf-folder in an S3 path.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix (folder path) to search within.
    """
    s3_client = boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")

    all_folders = set()
    parent_folders = set()
    svo_files = defaultdict(list)

    # Ensure prefix ends with a slash
    if not prefix.endswith('/'):
        prefix += '/'

    print(f"Finding leaf folders and .svo files in s3://{bucket_name}/{prefix}...")

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

    leaf_folders = sorted(list(all_folders - parent_folders))

    if not leaf_folders:
        print("No leaf folders found.")
        return

    print(f"Found {len(leaf_folders)} leaf folders.")

    # Second pass: download files from leaf folders
    for folder in leaf_folders:
        files_to_download = svo_files[folder]
        if not files_to_download:
            print(f"\nNo .svo files found in {folder}. Skipping.")
            continue

        # Calculate 5% of files to download, rounding up
        num_to_download = math.ceil(len(files_to_download) * 0.05)
        
        # Get the relative path for the local directory
        relative_folder_path = os.path.relpath(folder, prefix)
        local_dir = os.path.join("data", "svo-frames", relative_folder_path)
        os.makedirs(local_dir, exist_ok=True)

        print(f"\nDownloading {num_to_download} of {len(files_to_download)} .svo files from '{folder}' to '{local_dir}'...")

        # Select the first 5% of files
        download_list = files_to_download[:num_to_download]

        with tqdm(total=len(download_list), unit="file", desc=f"Folder {relative_folder_path}") as pbar:
            for s3_key in download_list:
                local_file_path = os.path.join(local_dir, os.path.basename(s3_key))
                try:
                    s3_client.download_file(bucket_name, s3_key, local_file_path)
                except Exception as e:
                    print(f"Error downloading {s3_key}: {e}")
                pbar.update(1)

if __name__ == "__main__":
    S3_BUCKET = "sg-new-data"
    S3_PREFIX = "dairy_farm/"
    get_svo_files(S3_BUCKET, S3_PREFIX)
