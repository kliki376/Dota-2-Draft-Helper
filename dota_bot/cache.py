import json
import time
from pathlib import Path
from typing import Any


class Cache:
    def __init__(self, path: str, ttl_seconds: int):
        self.path = path
        self.ttl_seconds = ttl_seconds
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        try:
            with open(self.path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict) -> None:
        with open(self.path, "w") as f:
            json.dump(data, f)

    def get(self, key: str) -> Any | None:
        data = self._load()
        entry = data.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires_at"]:
            return None
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        data = self._load()
        data[key] = {"value": value, "expires_at": time.time() + self.ttl_seconds}
        self._save(data)

    def delete(self, key: str) -> None:
        data = self._load()
        data.pop(key, None)
        self._save(data)

    def clear(self) -> None:
        self._save({})
