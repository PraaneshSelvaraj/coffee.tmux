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
    with patch("builtins.open", m):
        lfm.write_lock_file(data)
        m.assert_called_once_with(lfm.LOCK_FILE_PATH, "w")


def test_write_lock_file_exception(capsys: Any) -> None:
    data: lfm.LockData = {"plugins": []}
    with patch("builtins.open", side_effect=Exception("Write error")):
        lfm.write_lock_file(data)
        captured = capsys.readouterr()
        assert "Error writing lock file:" in captured.out
