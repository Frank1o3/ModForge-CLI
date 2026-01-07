#!/usr/bin/env bash
set -euo pipefail

REPO="Frank1o3/smithpy"

RAW_BASE="https://raw.githubusercontent.com/$REPO/main"
RELEASE_BASE="https://github.com/$REPO/releases/latest/download"

FILES=(
  "pyproject.toml"
  "README.md"
  "LICENSE"
)

ARCHIVES=(
  "src.tar.gz"
  "configs.tar.gz"
)

echo "Downloading SmithPy runtime files..."

# --- fetch top-level files ---
for file in "${FILES[@]}"; do
  echo "Downloading $file"
  curl -fsSL "$RAW_BASE/$file" -o "$file"
done

# --- fetch and extract runtime archives ---
for archive in "${ARCHIVES[@]}"; do
  echo "Downloading $archive"
  curl -fsSL "$RELEASE_BASE/$archive" -o "$archive"

  echo "Extracting $archive"
  tar -xzf "$archive"
  rm -f "$archive"
done

echo "SmithPy downloaded successfully."
