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
from .pluginInstaller import PluginInstaller
from .pluginLoader import PluginLoader
from .pluginRemover import PluginRemover
from .pluginSourcer import PluginSourcer
from .pluginUpdater import PluginUpdater

__all__ = [
    "PluginSourcer",
    "PluginInstaller",
    "PluginRemover",
    "PluginUpdater",
    "PluginLoader",
    "lock_file_manager",
]
