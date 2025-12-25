"""
coffee.tmux
Author: Praanesh S

Modules:
- pluginInstaller: Handles the installation of plugins.
- pluginLoader: Manages loading of plugins.
- pluginSourcer: Handles sourcing and configuration.
- pluginUpdater: Manages plugin updates.
- pluginRemover: Manages plugin removals.
"""

from . import lock_file_manager
from .plugin_installer import PluginInstaller
from .plugin_loader import PluginLoader
from .plugin_remover import PluginRemover
from .plugin_sourcer import PluginSourcer
from .plugin_updater import PluginUpdater

__all__ = [
    "PluginSourcer",
    "PluginInstaller",
    "PluginRemover",
    "PluginUpdater",
    "PluginLoader",
    "lock_file_manager",
]
