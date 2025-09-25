from typing import Any

from core import PluginSourcer
from core import lock_file_manager as lfm

from .tabs.home import HomeTab

plugin_sourcer = PluginSourcer()


def toggle_plugin(app_state: Any) -> None:
    display_list = HomeTab().get_display_list()
    if app_state.current_selection < len(display_list):
        selected_item = display_list[app_state.current_selection]
        if selected_item["type"] == "plugin":
            plugin = selected_item["data"]
            name = plugin["name"]
            lock_data = lfm.read_lock_file()
            for p in lock_data.get("plugins", []):
                if p["name"] == name:
                    p["enabled"] = not p.get("enabled", False)
                    lfm.write_lock_file(lock_data)
                    if p["enabled"]:
                        plugin_sourcer.activate_plugin(name)
                    else:
                        plugin_sourcer.deactivate_plugin(name)
                    break
