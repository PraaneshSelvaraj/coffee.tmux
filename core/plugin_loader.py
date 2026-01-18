import os
from typing import Any

import yaml


class PluginLoader:
    def __init__(self, path: str) -> None:
        self.coffee_plugins_list_dir: str = path

    def load_plugins(self) -> list[dict[str, Any]]:
        plugins: list[dict[str, Any]] = []

        if not os.path.exists(self.coffee_plugins_list_dir):
            raise FileNotFoundError(
                f"The plugin directory '{self.coffee_plugins_list_dir}' doesn't exist."
            )

        for filename in os.listdir(self.coffee_plugins_list_dir):
            if not filename.endswith((".yaml", ".yml")):
                continue

            file_path = os.path.join(self.coffee_plugins_list_dir, filename)

            try:
                with open(file_path, "r") as f:
                    raw = yaml.safe_load(f) or {}

                plugin = self._build_plugin_config(raw)

                if self._is_valid_plugin(plugin):
                    plugins.append(plugin)

            except Exception as e:
                print(f"[coffee] Failed to load {file_path}: {e}")

        return plugins

    def _build_plugin_config(self, data: dict[str, Any]) -> dict[str, Any]:
        url = (data.get("url") or "").strip()

        name = (data.get("name") or "").strip()
        if not name and url:
            name = self._derive_name_from_url(url)

        return {
            "name": name,
            "url": url,
            "local": bool(data.get("local", False)),
            "source": data.get("source", []) or [],
            "tag": data.get("tag"),
            "skip_auto_update": bool(data.get("skip_auto_update", False)),
        }

    def _is_valid_plugin(self, plugin: dict[str, Any]) -> bool:
        url = plugin.get("url")

        return isinstance(url, str) and url.strip() != ""

    def _derive_name_from_url(self, url: str) -> str:
        base = url.rstrip("/").split("/")[-1]
        return base.removesuffix(".git")
