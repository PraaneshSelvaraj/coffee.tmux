from unittest.mock import MagicMock, mock_open, patch

from core import PluginMigrator


def make_migrator(
    config_dir: str = "/fake/config",
    tmux_paths: list[str] | None = None,
) -> PluginMigrator:
    return PluginMigrator(
        coffee_config_dir=config_dir,
        tmux_conf_paths=tmux_paths or ["/fake/tmux.conf"],
    )


def exists_tmux_only(path: str) -> bool:
    return path == "/fake/tmux.conf"


def exists_tmux_and_yaml(path: str) -> bool:
    if path == "/fake/tmux.conf":
        return True
    return path.endswith(".yaml")


@patch("os.path.exists", side_effect=exists_tmux_only)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="""
set -g @plugin 'tmux-plugins/tmux-sensible'
set -g @plugin "tmux-plugins/tmux-resurrect"
run '~/.tmux/plugins/tpm/tpm'
""",
)
def test_discover_detects_plugins_and_tpm(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
) -> None:
    migrator = make_migrator()

    plan = migrator.discover()

    assert plan["plugins"] == [
        "tmux-plugins/tmux-resurrect",
        "tmux-plugins/tmux-sensible",
    ]
    assert plan["tpm_detected"] is True


@patch("os.path.exists", side_effect=exists_tmux_only)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="set -g @plugin 'tmux-plugins/tpm'",
)
def test_discover_skips_tpm_plugin(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
) -> None:
    migrator = make_migrator()

    plan = migrator.discover()

    assert plan["plugins"] == []


@patch("os.path.exists", side_effect=exists_tmux_and_yaml)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="set -g @plugin 'tmux-plugins/tmux-sensible'",
)
def test_discover_plans_create_and_skip(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
) -> None:
    migrator = make_migrator()

    plan = migrator.discover()

    assert plan["planned"]["to_create"] == []
    assert len(plan["planned"]["to_skip"]) == 1


@patch("os.path.exists", side_effect=exists_tmux_only)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="set -g @plugin 'tmux-plugins/tmux-sensible'",
)
def test_discover_no_existing_configs(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
) -> None:
    migrator = make_migrator()

    plan = migrator.discover()

    assert len(plan["planned"]["to_create"]) == 1
    assert plan["planned"]["to_skip"] == []


@patch("os.makedirs")
@patch("os.path.exists", side_effect=exists_tmux_only)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="set -g @plugin 'tmux-plugins/tmux-sensible'",
)
def test_apply_creates_yaml(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
    mock_makedirs: MagicMock,
) -> None:
    migrator = make_migrator()

    result = migrator.apply()

    assert result["generated_files"]
    assert result["skipped_files"] == []


@patch("os.makedirs")
@patch("os.path.exists", side_effect=exists_tmux_and_yaml)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="set -g @plugin 'tmux-plugins/tmux-sensible'",
)
def test_apply_skips_existing_file(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
    mock_makedirs: MagicMock,
) -> None:
    migrator = make_migrator()

    result = migrator.apply(overwrite=False)

    assert result["generated_files"] == []
    assert result["skipped_files"]


@patch("os.makedirs")
@patch("os.path.exists", side_effect=exists_tmux_and_yaml)
@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="set -g @plugin 'tmux-plugins/tmux-sensible'",
)
def test_apply_overwrite_rewrites(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
    mock_makedirs: MagicMock,
) -> None:
    migrator = make_migrator()

    result = migrator.apply(overwrite=True)

    assert result["generated_files"]
    assert result["skipped_files"] == []


@patch("os.makedirs")
@patch("os.path.exists", side_effect=exists_tmux_only)
@patch(
    "builtins.open",
    side_effect=OSError("permission denied"),
)
def test_apply_write_failure_adds_warning(
    mock_open_file: MagicMock,
    mock_exists: MagicMock,
    mock_makedirs: MagicMock,
) -> None:
    migrator = make_migrator()

    result = migrator.apply()

    assert result["warnings"]
