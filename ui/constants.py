import os

from rich.style import Style

PLUGINS_DIR = os.path.expanduser("~/.tmux/coffee/plugins")
TMUX_CONFIG_DIR = os.path.expanduser("~/.config/tmux/")
COFFEE_DIR = os.path.expanduser("~/.tmux/coffee")
COFFEE_PLUGINS_LIST_DIR = os.path.join(TMUX_CONFIG_DIR, "coffee/plugins")
COFFEE_INSTALLED_PLUGINS_DIR = os.path.join(COFFEE_DIR, "plugins")
LOCK_FILE_PATH = os.path.join(COFFEE_DIR, "caffeine-lock.json")

VISIBLE_ROWS = 10
TABS = ["Home", "Install", "Update", "Remove"]

ACCENT_COLOR = "#7aa2f7"
BACKGROUND_COLOR = "#1a1b26"
HIGHLIGHT_COLOR = "#9ece6a"
SELECTION_COLOR = "#bb9af7"
SECTION_COLOR = "#e0af68"
BACKGROUND_STYLE = Style(bgcolor=BACKGROUND_COLOR)
