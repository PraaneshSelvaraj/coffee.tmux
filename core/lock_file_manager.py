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
    try:
        with open(LOCK_FILE_PATH, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error writing lock file: {e}")
