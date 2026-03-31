#!/usr/bin/env bash

set -e

INSTALL_DIR="$HOME/.local/share/coffee"

echo "Setting up coffee.tmux..."

cd "$INSTALL_DIR" || {
  echo "Error: repository not found at $INSTALL_DIR"
  exit 1
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required"
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo "Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt

if [ -f "$INSTALL_DIR/bin/coffee" ]; then
  chmod +x "$INSTALL_DIR/bin/coffee"
fi

echo "Installation complete."
