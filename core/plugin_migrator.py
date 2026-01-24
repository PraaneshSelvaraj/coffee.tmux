import os
import re
from typing import Any, Iterable, List, Set

import yaml


class PluginMigrator:
    TPM_PLUGIN_PATTERN = re.compile(r"""^\s*set\s+-g\s+@plugin\s+['"]([^'"]+)['"]""")
    TPM_BOOTSTRAP_PATTERN = re.compile(r"""run(?:-shell)?\s+['"].*tpm.*['"]""")

    def __init__(
        self,
        coffee_config_dir: str,
        tmux_conf_paths: Iterable[str] | None = None,
    ) -> None:
        self.coffee_config_dir = os.path.expanduser(coffee_config_dir)
        self.tmux_conf_paths = (
            list(tmux_conf_paths)
            if tmux_conf_paths is not None
            else self._discover_tmux_conf_paths()
        )
        self._warnings: List[str] = []

    def discover(self) -> dict[str, Any]:
        plugins, tpm_detected = self._scan_tmux_configs()

        to_create: List[str] = []
        to_skip: List[str] = []

        for plugin in plugins:
            name = self._derive_plugin_name(plugin)
            path = os.path.join(self.coffee_config_dir, f"{name}.yaml")
            if os.path.exists(path):
                to_skip.append(path)
            else:
                to_create.append(path)

        return {
            "plugins": sorted(plugins),
            "tpm_detected": tpm_detected,
            "tmux_conf_paths": self.tmux_conf_paths,
            "planned": {
                "to_create": to_create,
                "to_skip": to_skip,
            },
            "warnings": self._warnings,
        }

    def apply(self, overwrite: bool = False) -> dict[str, Any]:
        plugins, tpm_detected = self._scan_tmux_configs()

        generated_files: List[str] = []
        skipped_files: List[str] = []

        for plugin in plugins:
            result = self._write_plugin_yaml(plugin, overwrite=overwrite)
            if result:
                if result["created"]:
                    generated_files.append(result["path"])
                else:
                    skipped_files.append(result["path"])

        return {
            "plugins": sorted(plugins),
            "generated_files": generated_files,
            "skipped_files": skipped_files,
            "tpm_detected": tpm_detected,
            "tmux_conf_paths": self.tmux_conf_paths,
            "warnings": self._warnings,
        }

    def _discover_tmux_conf_paths(self) -> List[str]:
        paths: List[str] = []

        env_tmux_conf = os.environ.get("TMUX_CONF")
        if env_tmux_conf:
            paths.append(env_tmux_conf)

        xdg_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        candidates = [
            os.path.join(xdg_home, "tmux", "tmux.conf"),
            os.path.expanduser("~/.tmux.conf"),
        ]

        for path in candidates:
            if os.path.exists(path):
                paths.append(path)

        seen = set()
        unique_paths: List[str] = []
        for p in paths:
            p = os.path.abspath(os.path.expanduser(p))
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)

        return unique_paths

    def _scan_tmux_configs(self) -> tuple[Set[str], bool]:
        plugins: Set[str] = set()
        tpm_detected = False

        for path in self.tmux_conf_paths:
            if not os.path.exists(path):
                continue

            try:
                with open(path, "r") as f:
                    for line in f:
                        plugin = self._parse_plugin_line(line)
                        if plugin and plugin != "tmux-plugins/tpm":
                            plugins.add(plugin)

                        if self.TPM_BOOTSTRAP_PATTERN.search(line):
                            tpm_detected = True
            except (IOError, UnicodeDecodeError) as e:
                self._warnings.append(f"Could not read {path}: {e}")

        return plugins, tpm_detected

    def _parse_plugin_line(self, line: str) -> str | None:
        match = self.TPM_PLUGIN_PATTERN.match(line)
        if not match:
            return None
        return match.group(1).strip()

    def _write_plugin_yaml(
        self, plugin: str, overwrite: bool = False
    ) -> dict[str, Any] | None:
        os.makedirs(self.coffee_config_dir, exist_ok=True)

        name = self._derive_plugin_name(plugin)
        path = os.path.join(self.coffee_config_dir, f"{name}.yaml")

        if os.path.exists(path) and not overwrite:
            return {"path": path, "created": False}

        try:
            with open(path, "w") as f:
                yaml.safe_dump(
                    {"url": plugin},
                    f,
                    sort_keys=False,
                    default_flow_style=False,
                )
            return {"path": path, "created": True}
        except IOError as e:
            self._warnings.append(f"Could not write {path}: {e}")
            return None

    def _derive_plugin_name(self, repo: str) -> str:
        return repo.rstrip("/").split("/")[-1]
