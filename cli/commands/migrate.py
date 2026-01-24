"""
Migrate command implementation
"""

from typing import Any

from core import PluginMigrator

from ..utils import (
    COFFEE_CONFIG_DIR,
    confirm_action,
    print_info,
    print_success,
    print_warning,
)


class Args:
    overwrite: bool


def run(args: Args) -> int:
    try:
        print_info("Scanning tmux configuration...")
        migrator = PluginMigrator(COFFEE_CONFIG_DIR)
        plan: dict[str, Any] = migrator.discover()

        warnings = plan.get("warnings", [])
        for warning in warnings:
            print_warning(warning)

        tmux_paths = plan.get("tmux_conf_paths", [])
        if tmux_paths:
            print("Found tmux config files:")
            for path in tmux_paths:
                print(f"  • {path}")
        else:
            print_warning("No tmux config files found")
            return 0

        plugins = plan.get("plugins", [])
        if not plugins:
            print_info("No plugins detected")
            return 0

        print(f"{len(plugins)} plugin(s) detected")

        planned = plan.get("planned", {})
        to_create = planned.get("to_create", [])
        to_skip = planned.get("to_skip", [])

        if to_skip and not args.overwrite:
            print_info(
                f"{len(to_skip)} plugin config(s) already exist and will be skipped"
            )

        if not to_create and not args.overwrite:
            print_success(
                "All plugin configs already exist. Use --overwrite to regenerate."
            )
            return 0

        if to_create and not args.overwrite:
            print_info(f"This will create {len(to_create)} plugin config file(s) in:")
            print(f"  {COFFEE_CONFIG_DIR}")

            if not confirm_action("Continue with migration?", default=False):
                print_info("Migration cancelled")
                return 0

        elif args.overwrite:
            total = len(to_create) + len(to_skip)
            print_info(f"This will overwrite {total} plugin config file(s) in:")
            print(f"  {COFFEE_CONFIG_DIR}")

            if not confirm_action("Continue with overwrite?", default=False):
                print_info("Migration cancelled")
                return 0

        result = migrator.apply(overwrite=args.overwrite)

        generated = result.get("generated_files", [])
        skipped = result.get("skipped_files", [])

        if generated:
            print_success(f"{len(generated)} plugin config(s) created")

        if skipped:
            print_info(f"{len(skipped)} existing plugin config(s) skipped")

        if result.get("tpm_detected", False):
            print_warning("TPM initialization code detected in your tmux config")
            print_warning(
                "After verifying Coffee works, you can remove the 'run' line that loads TPM"
            )

        apply_warnings = result.get("warnings", [])
        for warning in apply_warnings:
            if warning not in warnings:
                print_warning(warning)

        return 0

    except Exception as e:
        print_warning(f"Migration failed: {e}")
        return 1
