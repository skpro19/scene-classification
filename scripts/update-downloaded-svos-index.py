import os
import json
import argparse

def main():
    """
    Updates index file with SVO files already downloaded in the specified directory.
    Prepends the S3 URI prefix to the file locations.
    """
    parser = argparse.ArgumentParser(description='Update downloaded SVOs index')
    parser.add_argument('--index-file', default='index/downloaded-svos.json',
                       help='Path to the index file (default: index/downloaded-svos.json)')
    parser.add_argument('--svo-files-dir', default='data/svo-files',
                       help='Directory containing downloaded SVO files (default: data/svo-files)')
    parser.add_argument('--s3-uri-prefix', default='s3://sg-new-data/dairy_farm',
                       help='S3 URI prefix to prepend to file paths (default: s3://sg-new-data/dairy_farm)')
    
    args = parser.parse_args()
    
    index_file = args.index_file
    svo_files_dir = args.svo_files_dir
    s3_uri_prefix = args.s3_uri_prefix
    
    # Create index directory if it doesn't exist
    os.makedirs(os.path.dirname(index_file), exist_ok=True)
    
    downloaded_files = []
    
    # Walk through the svo-files directory
    for root, dirs, files in os.walk(svo_files_dir):
        for file in files:
            if file.endswith('.svo'):
                # Get the relative path from svo-files directory
                rel_path = os.path.relpath(os.path.join(root, file), svo_files_dir)
                # Convert to S3 path format
                s3_path = f"{s3_uri_prefix}/{rel_path}"
                downloaded_files.append(s3_path)
    
    # Load existing index if it exists
    existing_files = []
    if os.path.exists(index_file):
        try:
            with open(index_file, 'r') as f:
                existing_files = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing_files = []
    
    # Combine existing and new files, removing duplicates
    all_files = list(set(existing_files + downloaded_files))
    all_files.sort()  # Sort for consistent ordering
    
    # Write updated index
    with open(index_file, 'w') as f:
        json.dump(all_files, f, indent=2)
    
    print(f"Updated {index_file} with {len(all_files)} total files")
    return all_files

if __name__ == "__main__":
    main() 