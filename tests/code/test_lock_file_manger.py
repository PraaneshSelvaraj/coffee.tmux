from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import core.lock_file_manager as lfm


def test_read_lock_file_success() -> None:
    sample_data = '{"plugins": [{"name": "test"}]}'
    with (
        patch("core.lock_file_manager._file_lock"),
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=sample_data)),
    ):
        data = lfm.read_lock_file()
    assert data["plugins"][0]["name"] == "test"


def test_read_lock_file_missing_file_returns_empty() -> None:
    with (
        patch("core.lock_file_manager._file_lock"),
        patch("os.path.exists", return_value=False),
    ):
        data = lfm.read_lock_file()
    assert data == {"plugins": []}


def test_read_lock_file_corrupt_json_returns_empty() -> None:
    with (
        patch("core.lock_file_manager._file_lock"),
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data="{invalid json")),
    ):
        data = lfm.read_lock_file()
    assert data == {"plugins": []}


def test_write_lock_file_success() -> None:
    data: lfm.LockData = {"plugins": []}

    m = mock_open()
    mock_file = m.return_value
    mock_file.fileno.return_value = 42

    with (
        patch("core.lock_file_manager._file_lock"),
        patch("core.lock_file_manager.os.makedirs"),
        patch("builtins.open", m),
        patch("os.fsync") as mock_fsync,
        patch("os.replace") as mock_replace,
    ):
        lfm.write_lock_file(data)

        m.assert_called_once_with(lfm.LOCK_FILE_PATH + ".tmp", "w")
        mock_file.flush.assert_called_once()
        mock_file.fileno.assert_called_once()
        mock_fsync.assert_called_once_with(42)
        mock_replace.assert_called_once_with(
            lfm.LOCK_FILE_PATH + ".tmp",
            lfm.LOCK_FILE_PATH,
        )


def test_write_lock_file_open_error_raises_and_cleans_up() -> None:
    data: lfm.LockData = {"plugins": []}

    with (
        patch("core.lock_file_manager._file_lock"),
        patch("core.lock_file_manager.os.makedirs"),
        patch("builtins.open", side_effect=Exception("Write error")),
        patch("os.path.exists", return_value=True),
        patch("os.remove") as mock_remove,
    ):
        try:
            lfm.write_lock_file(data)
        except IOError as exc:
            assert "Error writing lock file" in str(exc)
            assert exc.__cause__ is not None
            assert "Write error" in str(exc.__cause__)
        else:
            raise AssertionError("Expected IOError to be raised")

        mock_remove.assert_called_once_with(lfm.LOCK_FILE_PATH + ".tmp")


def test_write_lock_file_rename_failure_raises_and_cleans_up() -> None:
    data: lfm.LockData = {"plugins": []}

    m = mock_open()
    mock_file = m.return_value
    mock_file.fileno.return_value = 42

    with (
        patch("core.lock_file_manager._file_lock"),
        patch("core.lock_file_manager.os.makedirs"),
        patch("builtins.open", m),
        patch("os.fsync"),
        patch("os.replace", side_effect=Exception("Rename failed")),
        patch("os.path.exists", return_value=True),
        patch("os.remove") as mock_remove,
    ):
        try:
            lfm.write_lock_file(data)
        except IOError as exc:
            assert "Error writing lock file" in str(exc)
            assert exc.__cause__ is not None
            assert "Rename failed" in str(exc.__cause__)
        else:
            raise AssertionError("Expected IOError to be raised")

        mock_remove.assert_called_once_with(lfm.LOCK_FILE_PATH + ".tmp")


def test_write_lock_file_error_without_temp_file() -> None:
    data: lfm.LockData = {"plugins": []}

    with (
        patch("core.lock_file_manager._file_lock"),
        patch("core.lock_file_manager.os.makedirs"),
        patch("builtins.open", side_effect=Exception("Write error")),
        patch("os.path.exists", return_value=False),
        patch("os.remove") as mock_remove,
    ):
        try:
            lfm.write_lock_file(data)
        except IOError as exc:
            assert "Error writing lock file" in str(exc)
        else:
            raise AssertionError("Expected IOError to be raised")

        mock_remove.assert_not_called()


def test_file_lock_creates_and_removes_flag_file(tmp_path: Any) -> None:
    """_file_lock should create and then remove the flag file."""
    coffee_dir = tmp_path / ".tmux" / "coffee"
    lock_flag = coffee_dir / ".caffeine.lock"

    with (
        patch("core.lock_file_manager.COFFEE_DIR", str(coffee_dir)),
        patch("core.lock_file_manager.LOCK_FLAG_FILE", str(lock_flag)),
    ):
        from core.lock_file_manager import _file_lock  # type: ignore

        with _file_lock():
            assert lock_flag.exists()
        assert not lock_flag.exists()


def test_file_lock_timeout_raises_timeouterror() -> None:
    """If lock file persists and is 'fresh', timeout should raise."""
    fake_time = MagicMock()
    fake_time.side_effect = [0.0, 6.0, 6.0, 6.0]

    def fake_stat(path: str) -> Any:
        class S:
            st_mtime = 5.0

        return S()

    with (
        patch("core.lock_file_manager.time.time", fake_time),
        patch("core.lock_file_manager.os.makedirs"),
        patch("core.lock_file_manager.os.open", side_effect=FileExistsError()),
        patch("core.lock_file_manager.os.stat", side_effect=fake_stat),
    ):
        from core.lock_file_manager import _file_lock  # type: ignore

        try:
            with _file_lock(timeout=5.0):
                pass
        except TimeoutError as exc:
            assert "Could not acquire lock" in str(exc)
        else:
            raise AssertionError("Expected TimeoutError to be raised")
