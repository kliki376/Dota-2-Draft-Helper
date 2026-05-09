import json
from pathlib import Path


class ProfileStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        try:
            with open(self.path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict) -> None:
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def get(self, user_id: int) -> int | None:
        val = self._load().get(str(user_id))
        return int(val) if val is not None else None

    def set(self, user_id: int, account_id: int) -> None:
        data = self._load()
        data[str(user_id)] = account_id
        self._save(data)

    def remove(self, user_id: int) -> None:
        data = self._load()
        data.pop(str(user_id), None)
        self._save(data)
