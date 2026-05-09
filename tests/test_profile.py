import pytest
from dota_bot.profile import ProfileStore


@pytest.fixture
def store(tmp_path):
    return ProfileStore(str(tmp_path / "players.json"))


def test_get_returns_none_when_no_profile(store):
    assert store.get(12345) is None


def test_set_and_get_profile(store):
    store.set(12345, 987654321)
    assert store.get(12345) == 987654321


def test_remove_profile(store):
    store.set(12345, 987654321)
    store.remove(12345)
    assert store.get(12345) is None


def test_remove_nonexistent_is_safe(store):
    store.remove(99999)  # should not raise


def test_multiple_users_independent(store):
    store.set(1, 111)
    store.set(2, 222)
    assert store.get(1) == 111
    assert store.get(2) == 222
    store.remove(1)
    assert store.get(1) is None
    assert store.get(2) == 222


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "players.json")
    store1 = ProfileStore(path)
    store1.set(42, 123456)
    store2 = ProfileStore(path)
    assert store2.get(42) == 123456
