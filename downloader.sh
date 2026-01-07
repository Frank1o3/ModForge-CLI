#!/usr/bin/env bash
set -e

REPO="Frank1o3/smithpy"
BRANCH="main"
RAW="https://raw.githubusercontent.com/$REPO/$BRANCH"

FILES=(
  "pyproject.toml"
  "README.md"
  "LICENSE"
)

DIRS=(
  "src"
  "configs"
)

echo "Downloading SmithPy..."

# files
for file in "${FILES[@]}"; do
  curl -fsSL "$RAW/$file" -o "$file"
done

# directories
for dir in "${DIRS[@]}"; do
  echo "Fetching $dir/"
  curl -fsSL "$RAW/$dir.tar.gz" -o "$dir.tar.gz" || {
    echo "Error: $dir archive not found"
    exit 1
  }
  tar -xzf "$dir.tar.gz"
  rm "$dir.tar.gz"
done

echo "Done."
