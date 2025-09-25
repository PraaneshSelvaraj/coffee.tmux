#!/usr/bin/env python3
"""
Coffee TUI entry point for tmux popup
"""
import os
import sys
import threading

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from core import PluginRemover, PluginUpdater
from ui.app import PluginManagerApp
from ui.constants import PLUGINS_DIR


def run_auto_update_in_background() -> None:
    updater = PluginUpdater(PLUGINS_DIR)

    def worker() -> None:
        try:
            updater.auto_update_all()
        except Exception:
            pass

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def main() -> None:
    run_auto_update_in_background()
    plugin_remover = PluginRemover(PLUGINS_DIR)
    plugin_updater = PluginUpdater(PLUGINS_DIR)
    app = PluginManagerApp(plugin_updater, plugin_remover)
    app.run()


if __name__ == "__main__":
    main()
