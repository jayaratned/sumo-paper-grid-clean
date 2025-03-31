#!/bin/bash

set -e  # Exit on error

logfile="dvc_add_log.txt"
echo "🔁 Sync started at $(date)" >> "$logfile"

# === Only check folders where data might live ===
TARGET_DIRS=("sumo-operational-project" "sumo-safety-traci-project" "sumo-tester" "sumo-traci-project" "static-attacker" "other")

is_dvc_tracked() {
    local file="$1"
    [[ -f "${file}.dvc" ]] || grep -q "$file" .gitignore 2>/dev/null
}

echo "🔍 Adding large files (.csv, .zip)..."

for dir in "${TARGET_DIRS[@]}"; do
    [ -d "$dir" ] || continue
    find "$dir" -type f \( -name "*.csv" -o -name "*.zip" \) | while read file; do
        if is_dvc_tracked "$file"; then
            echo "⏩ Skipping (already tracked): $file" >> "$logfile"
        else
            echo "📦 Adding: $file"
            echo "📦 Adding: $file" >> "$logfile"
            if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
                echo "🔀 Removing Git tracking from $file"
                git rm --cached "$file"
            fi
            dvc add "$file" >> "$logfile" 2>&1 || echo "⚠️ Failed: $file" >> "$logfile"
        fi
    done
done

echo "🔍 Adding other files >50MB..."

for dir in "${TARGET_DIRS[@]}"; do
    [ -d "$dir" ] || continue
    find "$dir" -type f -size +50M ! -name "*.dvc" | while read file; do
        if is_dvc_tracked "$file"; then
            echo "⏩ Skipping (already tracked): $file" >> "$logfile"
        else
            echo "📦 Adding large: $file"
            echo "📦 Adding large: $file" >> "$logfile"
            if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
                echo "🔀 Removing Git tracking from $file"
                git rm --cached "$file"
            fi
            dvc add "$file" >> "$logfile" 2>&1 || echo "⚠️ Failed: $file" >> "$logfile"
        fi
    done
done

echo "🧹 Removing deleted DVC-tracked files..."
dvc status -c | grep 'deleted' | awk '{print $2}' | while read deleted; do
    echo "❌ Removing from DVC: $deleted"
    echo "❌ Removing from DVC: $deleted" >> "$logfile"
    dvc remove "$deleted" --outs >> "$logfile" 2>&1
done

echo "📂 Staging everything for Git..."
git add . --all

echo "📝 Committing..."
git commit -m "Auto sync $(date +'%Y-%m-%d %H:%M')"

echo "🚀 Pushing to GitHub..."
git push

echo "☁️ Checking what DVC will push:"
dvc status -c >> "$logfile"

echo "☁️ Pushing to DVC remote..."
dvc push >> "$logfile" 2>&1

echo "✅ Done. Everything synced!"
