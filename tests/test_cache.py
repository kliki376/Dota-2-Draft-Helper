import json
import time
import pytest
from dota_bot.cache import Cache


@pytest.fixture
def tmp_cache(tmp_path):
    return Cache(str(tmp_path / "cache.json"), ttl_seconds=2)


def test_get_missing_key_returns_none(tmp_cache):
    assert tmp_cache.get("nonexistent") is None


def test_set_and_get_value(tmp_cache):
    tmp_cache.set("heroes", [{"id": 1, "name": "antimage"}])
    assert tmp_cache.get("heroes") == [{"id": 1, "name": "antimage"}]


def test_expired_key_returns_none(tmp_cache):
    tmp_cache.set("heroes", [{"id": 1}])
    data = json.loads(open(tmp_cache.path).read())
    data["heroes"]["expires_at"] = time.time() - 1
    with open(tmp_cache.path, "w") as f:
        json.dump(data, f)
    assert tmp_cache.get("heroes") is None


def test_clear_removes_all_keys(tmp_cache):
    tmp_cache.set("key1", "value1")
    tmp_cache.set("key2", "value2")
    tmp_cache.clear()
    assert tmp_cache.get("key1") is None
    assert tmp_cache.get("key2") is None


def test_delete_removes_specific_key(tmp_cache):
    tmp_cache.set("keep", "this")
    tmp_cache.set("remove", "this")
    tmp_cache.delete("remove")
    assert tmp_cache.get("keep") == "this"
    assert tmp_cache.get("remove") is None
