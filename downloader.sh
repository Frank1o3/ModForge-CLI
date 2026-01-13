#!/usr/bin/env bash
set -euo pipefail

REPO="Frank1o3/smithpy"
PYTHON=${PYTHON:-python3}

echo "Installing SmithPy..."

# Ensure pip
$PYTHON -m ensurepip --upgrade || true

# Get latest wheel URL
WHEEL_URL=$(
  curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" |
  grep browser_download_url |
  grep '\.whl"' |
  cut -d '"' -f 4
)

if [ -z "$WHEEL_URL" ]; then
  echo "Failed to locate SmithPy wheel in latest release"
  exit 1
fi

echo "Downloading $WHEEL_URL"

$PYTHON -m pip install --upgrade "$WHEEL_URL"

echo "SmithPy installed successfully."
echo "Run: smithpy --help"
