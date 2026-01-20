import json
import os
import time
from contextlib import contextmanager
from typing import Any, Generator, TypedDict

COFFEE_DIR: str = os.path.expanduser("~/.tmux/coffee")
LOCK_FILE_PATH: str = os.path.join(COFFEE_DIR, "caffeine-lock.json")

# Lock configuration
LOCK_FLAG_FILE: str = os.path.join(COFFEE_DIR, ".caffeine.lock")
LOCK_TIMEOUT: float = 5.0
LOCK_POLL_INTERVAL: float = 0.05


class LockData(TypedDict):
    plugins: list[dict[str, Any]]


@contextmanager
def _file_lock(timeout: float = LOCK_TIMEOUT) -> Generator[None, None, None]:
    os.makedirs(COFFEE_DIR, exist_ok=True)
    start_time: float = time.time()

    # Try to acquire lock
    while True:
        try:
            # Atomically create lock file (fails if exists)
            fd = os.open(LOCK_FLAG_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break  # Lock acquired!

        except FileExistsError:
            # Another process holds the lock
            if time.time() - start_time >= timeout:
                # Timeout - check if lock is stale
                try:
                    stat: os.stat_result = os.stat(LOCK_FLAG_FILE)
                    age: float = time.time() - stat.st_mtime
                    if age > 30:  # Stale lock (30+ seconds old)
                        os.remove(LOCK_FLAG_FILE)
                        continue  # Retry
                except (FileNotFoundError, OSError):
                    continue  # Retry if lock disappeared

                raise TimeoutError(
                    f"Could not acquire lock after {timeout}s. "
                    "Another process may be using the lock file."
                )
            time.sleep(LOCK_POLL_INTERVAL)

    try:
        yield  # Critical section (read/write)
    finally:
        # Release lock
        try:
            os.remove(LOCK_FLAG_FILE)
        except FileNotFoundError:
            pass  # Already removed (race condition ok)


def read_lock_file() -> LockData:
    with _file_lock():
        try:
            if not os.path.exists(LOCK_FILE_PATH):
                return {"plugins": []}

            with open(LOCK_FILE_PATH, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"plugins": []}


def write_lock_file(data: LockData) -> None:
    temp_file: str = LOCK_FILE_PATH + ".tmp"

    with _file_lock():
        try:
            os.makedirs(COFFEE_DIR, exist_ok=True)

            with open(temp_file, "w") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, LOCK_FILE_PATH)
        except (OSError, ValueError, TypeError) as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            raise IOError(f"Error writing lock file") from e
