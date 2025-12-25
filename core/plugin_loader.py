import os
from typing import Any

import yaml


class PluginLoader:
    def __init__(self, path: str) -> None:
        self.coffee_plugins_list_dir: str = path

    def load_plugins(self) -> list[dict[str, Any]]:
        plugin_configs: list[dict[str, Any]] = []

        if not os.path.exists(self.coffee_plugins_list_dir):
            raise FileNotFoundError(
                f"The plugin directory '{self.coffee_plugins_list_dir}' doesn't exist."
            )

        for file in os.listdir(self.coffee_plugins_list_dir):
            if file.endswith(".yaml") or file.endswith(".yml"):
                file_path = os.path.join(self.coffee_plugins_list_dir, file)
                try:
                    with open(file_path, "r") as f:
                        data = yaml.safe_load(f)
                        if data:
                            plugin_data: dict[str, Any] = {
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
