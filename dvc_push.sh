#!/bin/bash

# Path where files are generated, with recursion into subdirectories
FILE_PATHS=("sumo-traci-project/data/" "sumo-safety-traci-project/")

# Loop through all paths
for path in "${FILE_PATHS[@]}"; do
  # Loop through all files in the specified path and its subdirectories
  find "$path" -type f | while read -r file; do
    # Check if the file size is greater than 100MB
    if [[ $(stat -c%s "$file") -gt 104857600 ]]; then
      # Construct the path to the potential .dvc file
      dvc_file="${file}.dvc"

      # Check if the DVC file exists
      if [[ -f "$dvc_file" ]]; then
        # Check if the file has changed since the last dvc add
        if dvc status "$file" | grep -q 'changed'; then
          # If the file has changed, re-add the file to DVC
          dvc add "$file"
        fi
      else
        # If the file is not yet tracked by DVC, add it
        dvc add "$file"
      fi

      # Git commit the changes (dvc files)
      git add "$dvc_file"
      git commit -m "Update large file in DVC: $(basename "$file")"

      # Push to DVC remote storage
      dvc push
    fi
  done
done
