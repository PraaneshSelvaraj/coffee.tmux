from typing import Any
from unittest.mock import mock_open, patch

import core.lock_file_manager as lfm


def test_read_lock_file_success() -> None:
    sample_data = '{"plugins": [{"name": "test"}]}'
    with patch("builtins.open", mock_open(read_data=sample_data)):
        data = lfm.read_lock_file()
        assert data["plugins"][0]["name"] == "test"


def test_read_lock_file_exception() -> None:
    with patch("builtins.open", side_effect=Exception("File error")):
        data = lfm.read_lock_file()
        assert data == {"plugins": []}


def test_write_lock_file_success() -> None:
    data: lfm.LockData = {"plugins": []}

    m = mock_open()
    mock_file = m.return_value
    mock_file.fileno.return_value = 42

    with (
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
            lfm.LOCK_FILE_PATH + ".tmp", lfm.LOCK_FILE_PATH
        )


def test_write_lock_file_exception(capsys: Any) -> None:
    data: lfm.LockData = {"plugins": []}

    with (
        patch("builtins.open", side_effect=Exception("Write error")),
        patch("os.path.exists", return_value=True),
        patch("os.remove") as mock_remove,
    ):
        lfm.write_lock_file(data)

        mock_remove.assert_called_once_with(lfm.LOCK_FILE_PATH + ".tmp")

        captured = capsys.readouterr()
        assert "Error writing lock file:" in captured.out


def test_write_lock_file_cleanup_on_rename_failure(capsys: Any) -> None:
    """Test cleanup when rename fails after successful write"""
    data: lfm.LockData = {"plugins": []}

    m = mock_open()
    mock_file = m.return_value
    mock_file.fileno.return_value = 42

    with (
        patch("builtins.open", m),
        patch("os.fsync"),
        patch("os.replace", side_effect=Exception("Rename failed")),
        patch("os.path.exists", return_value=True),
        patch("os.remove") as mock_remove,
    ):
        lfm.write_lock_file(data)

        mock_remove.assert_called_once_with(lfm.LOCK_FILE_PATH + ".tmp")

        captured = capsys.readouterr()
        assert "Error writing lock file:" in captured.out
