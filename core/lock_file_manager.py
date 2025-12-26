import json
import os
from typing import Any, TypedDict

COFFEE_DIR: str = os.path.expanduser("~/.tmux/coffee")
LOCK_FILE_PATH: str = os.path.join(COFFEE_DIR, "caffeine-lock.json")


class LockData(TypedDict):
    plugins: list[dict[str, Any]]


def read_lock_file() -> LockData:
    try:
        with open(LOCK_FILE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"plugins": []}


def write_lock_file(data: LockData) -> None:
    temp_file = LOCK_FILE_PATH + ".tmp"
    try:
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, LOCK_FILE_PATH)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        print(f"Error writing lock file: {e}")
