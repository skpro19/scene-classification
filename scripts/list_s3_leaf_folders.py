import boto3
import os
from collections import defaultdict

def list_s3_leaf_folders(bucket_name, prefix):
    """
    Lists all leaf-folders in an S3 path and counts the number of .svo files in each.

    A leaf-folder is a folder that does not have any further sub-folders.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix (folder path) to search within.
    """
    s3_client = boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")

    all_folders = set()
    parent_folders = set()
    svo_counts = defaultdict(int)

    # Ensure prefix ends with a slash
    if not prefix.endswith('/'):
        prefix += '/'

    print(f"Listing objects in s3://{bucket_name}/{prefix}...")

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            key = obj["Key"]
            # Get the directory part of the key
            folder = os.path.dirname(key)
            
            # Add the folder to our set of all folders
            if folder != prefix.strip('/'):
                 all_folders.add(folder)

            # Check if this object's folder is a parent folder
            # by checking if its path contains subdirectories relative to the prefix
            relative_path = os.path.relpath(folder, prefix)
            if '/' in relative_path:
                parent = os.path.join(prefix.strip('/'), relative_path.split('/')[0])
                parent_folders.add(parent)


            # Count .svo files
            if key.endswith(".svo"):
                svo_counts[folder] += 1
    
    # A leaf folder is any folder that is not a parent to another folder
    leaf_folders = all_folders - parent_folders

    if not leaf_folders:
        print("No leaf folders found.")
        return

    # Prepare data for table
    table_data = []
    for folder in sorted(list(leaf_folders)):
        table_data.append({
            "folder": f"s3://{bucket_name}/{folder}",
            "svo_count": svo_counts[folder],
        })

    # Print table
    if table_data:
        header = ["Leaf Folder Path", "SVO File Count"]
        # Determine column widths
        max_folder_len = max(len(header[0]), max(len(d["folder"]) for d in table_data))
        max_count_len = max(len(header[1]), max(len(str(d["svo_count"])) for d in table_data))

        # Print header
        print(f"{header[0]:<{max_folder_len}} | {header[1]:<{max_count_len}}")
        print(f"{'-' * max_folder_len}-+-{'-' * max_count_len}")

        # Print rows
        for item in table_data:
            print(f"{item['folder']:<{max_folder_len}} | {item['svo_count']:<{max_count_len}}")

if __name__ == "__main__":
    S3_BUCKET = "sg-new-data"
    S3_PREFIX = "dairy_farm/"
    list_s3_leaf_folders(S3_BUCKET, S3_PREFIX)
