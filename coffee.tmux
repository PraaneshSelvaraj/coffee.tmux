#!/usr/bin/env bash

COFFEE_DIR="$HOME/.local/share/coffee"
VENV_PY="$COFFEE_DIR/.venv/bin/python"

bind-key C run-shell "tmux display-popup -E '$VENV_PY $COFFEE_DIR/ui.py'"

run-shell "$VENV_PY $COFFEE_DIR/cli/main.py --source-plugins"
