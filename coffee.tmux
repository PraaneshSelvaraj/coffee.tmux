#!/usr/bin/env bash

COFFEE_DIR="$HOME/.local/share/coffee"

bind-key C run-shell "tmux display-popup -E \"python3 ${COFFEE_DIR}/ui.py\""

run-shell "python3 ${COFFEE_DIR}/cli/main.py --source-plugins"