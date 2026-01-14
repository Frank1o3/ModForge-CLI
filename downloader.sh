#!/usr/bin/env bash
set -euo pipefail

REPO="Frank1o3/ModForge-Cli"
PYTHON=${PYTHON:-python3}
OS="$(uname -s)"

echo "Installing ModForge-Cli..."

# Resolve latest wheel URL
WHEEL_URL="$(
  curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
  | grep -E '"browser_download_url".*\.whl"' \
  | head -n 1 \
  | cut -d '"' -f 4
)"

if [[ -z "$WHEEL_URL" ]]; then
  echo "Failed to locate ModForge-Cli wheel in latest release."
  exit 1
fi

case "$OS" in
  Linux*)
    echo "Detected Linux — using pipx"

    if ! command -v pipx >/dev/null 2>&1; then
      echo "pipx not found."
      echo
      echo "Please install pipx using your system package manager:"
      echo
      echo "  Arch Linux:   sudo pacman -S python-pipx"
      echo "  Debian/Ubuntu: sudo apt install pipx"
      echo "  Fedora:       sudo dnf install pipx"
      echo
      exit 1
    fi

    pipx install --force "$WHEEL_URL"
    ;;

  Darwin*)
    echo "Detected macOS — using pipx"

    if ! command -v pipx >/dev/null 2>&1; then
      echo "pipx not found. Installing via pip..."
      $PYTHON -m pip install --user pipx
      pipx ensurepath
    fi

    pipx install --force "$WHEEL_URL"
    ;;

  MINGW*|MSYS*|CYGWIN*)
    echo "Detected Windows — using pip"
    $PYTHON -m pip install --upgrade "$WHEEL_URL"
    ;;

  *)
    echo "Unsupported OS: $OS"
    exit 1
    ;;
esac

echo
echo "ModForge-Cli installed successfully."
echo "Run: ModForge-Cli --help"
