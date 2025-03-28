#!/bin/bash
set -e

# SUMO input file extensions (glob patterns)
extensions=("net.xml" "add.xml" "rou.xml" "poi.xml" "emi.xml")

echo "🔄 Removing SUMO input files from DVC..."

for ext in "${extensions[@]}"; do
  find . -type f -name "*.${ext}" | while read file; do
    if [ -f "${file}.dvc" ]; then
      echo "🧹 Removing from DVC: $file"
      dvc remove "${file}.dvc"
      rm -f "${file}.dvc"
      git add "$file"
    fi
  done
done

# Handle exact match for gui-settings.xml
find . -type f -name "gui-settings.xml" | while read file; do
  if [ -f "${file}.dvc" ]; then
    echo "🧹 Removing from DVC: $file"
    dvc remove "${file}.dvc"
    rm -f "${file}.dvc"
    git add "$file"
  fi
done

echo "✅ All matching files moved to Git tracking."

echo "📦 Committing changes..."
git commit -m "Moved SUMO input files from DVC to Git"

echo "🚫 Updating .dvcignore..."
{
  echo "*.net.xml"
  echo "*.add.xml"
  echo "*.rou.xml"
  echo "gui-settings.xml"
  echo "*.poi.xml"
  echo "*.emi.xml"
} >> .dvcignore

git add .dvcignore
git commit -m "Ignore SUMO input file types in DVC"

echo "✅ Done. SUMO inputs are now Git-tracked and excluded from DVC."
