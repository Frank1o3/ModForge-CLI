#!/usr/bin/env bash
set -euo pipefail

REPO="Frank1o3/smithpy"
PYTHON=${PYTHON:-python3}

echo "Installing SmithPy..."

$PYTHON -m ensurepip --upgrade || true

$PYTHON -m pip install --upgrade \
  https://github.com/$REPO/releases/latest/download/$(curl -fsSL \
    https://api.github.com/repos/$REPO/releases/latest \
    | grep '"browser_download_url".*\.whl"' \
    | cut -d '"' -f 4)

echo "SmithPy installed successfully."
echo "Run: smithpy --help"

