import os
from typing import Any, Dict, List

import yaml


class PluginLoader:
    def __init__(self, path: str) -> None:
        self.COFFEE_PLUGINS_LIST_DIR: str = path

    def load_plugins(self) -> List[Dict[str, Any]]:
        plugin_configs: List[Dict[str, Any]] = []

        if not os.path.exists(self.COFFEE_PLUGINS_LIST_DIR):
            raise FileNotFoundError(
                f"The plugin directory '{self.COFFEE_PLUGINS_LIST_DIR}' doesn't exist."
            )

        for file in os.listdir(self.COFFEE_PLUGINS_LIST_DIR):
            if file.endswith(".yaml") or file.endswith(".yml"):
                file_path = os.path.join(self.COFFEE_PLUGINS_LIST_DIR, file)
                try:
                    with open(file_path, "r") as f:
                        data = yaml.safe_load(f)
                        if data:
                            plugin_data: Dict[str, Any] = {
                                "name": data.get("name", ""),
                                "url": data.get("url", ""),
                                "local": data.get("local", False),
                                "source": data.get("source", []),
                                "tag": data.get("tag", None),
                                "skip_auto_update": data.get("skip_auto_update", False),
                            }
                            if plugin_data["name"] and plugin_data["url"]:
                                plugin_configs.append(plugin_data)
                except Exception as e:
                    print(f"Error Reading {file_path}: {e}")

        return plugin_configs
