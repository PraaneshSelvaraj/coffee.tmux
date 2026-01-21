"""
Coffee TUI entry point for tmux popup
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from core import PluginRemover, PluginUpdater, PluginUpgrader
from ui.app import PluginManagerApp
from ui.constants import PLUGINS_DIR


def main() -> None:
    plugin_remover = PluginRemover(PLUGINS_DIR)
    plugin_updater = PluginUpdater(PLUGINS_DIR)
    plugin_upgrader = PluginUpgrader()
    app = PluginManagerApp(plugin_updater, plugin_upgrader, plugin_remover)
    app.run()


if __name__ == "__main__":
    main()
