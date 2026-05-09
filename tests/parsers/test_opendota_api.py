import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from dota_bot.parsers.opendota_api import OpenDotaClient
from dota_bot.models import HeroInfo, HeroMeta, HeroMatchup, PlayerHeroStats

HEROES_JSON = [
    {"id": 1, "name": "npc_dota_hero_antimage", "localized_name": "Anti-Mage"},
    {"id": 5, "name": "npc_dota_hero_crystal_maiden", "localized_name": "Crystal Maiden"},
]

HERO_STATS_JSON = [
    {
        "id": 1, "name": "npc_dota_hero_antimage", "localized_name": "Anti-Mage",
        "pro_pick": 100, "pro_win": 55,
        "5_pick": 1000, "5_win": 490,
        "6_pick": 2000, "6_win": 980,
        "7_pick": 3000, "7_win": 1530,
        "8_pick": 4000, "8_win": 2100,
    },
    {
        "id": 5, "name": "npc_dota_hero_crystal_maiden", "localized_name": "Crystal Maiden",
        "pro_pick": 0, "pro_win": 0,
        "5_pick": 500, "5_win": 265,
        "6_pick": 1000, "6_win": 530,
        "7_pick": 1500, "7_win": 810,
        "8_pick": 2000, "8_win": 1080,
    },
]

# matchup data FROM hero 1 (Anti-Mage)'s perspective
MATCHUPS_JSON = [
    {"hero_id": 5, "games_played": 1000, "wins": 400},  # AM has 40% WR vs CM
    {"hero_id": 11, "games_played": 800, "wins": 480},  # AM has 60% WR vs Nevermore
]

PLAYER_HEROES_JSON = [
    {"hero_id": 1, "games": 150, "win": 82},
    {"hero_id": 5, "games": 3, "win": 1},
]

ID_TO_SLUG = {1: "antimage", 5: "crystal_maiden", 11: "nevermore"}


def _make_mock_resp(data):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = data
    return mock


@pytest.fixture
def client():
    return OpenDotaClient(api_key="")


async def test_get_heroes(client):
    mock_get = AsyncMock(return_value=_make_mock_resp(HEROES_JSON))
    with patch.object(client._http, "get", mock_get):
        heroes = await client.get_heroes()
    assert heroes == [
        HeroInfo(id=1, slug="antimage", localized_name="Anti-Mage"),
        HeroInfo(id=5, slug="crystal_maiden", localized_name="Crystal Maiden"),
    ]
    mock_get.assert_called_once_with("https://api.opendota.com/api/heroes")


async def test_get_hero_stats_winrate(client):
    mock_get = AsyncMock(return_value=_make_mock_resp(HERO_STATS_JSON))
    with patch.object(client._http, "get", mock_get):
        stats = await client.get_hero_stats()
    expected_wr = (490 + 980 + 1530 + 2100) / (1000 + 2000 + 3000 + 4000)
    assert abs(stats[1].win_rate - expected_wr) < 0.001
    assert stats[1].pro_pick == 100
    assert stats[1].pro_win == 55


async def test_get_hero_stats_pick_rate_normalized(client):
    mock_get = AsyncMock(return_value=_make_mock_resp(HERO_STATS_JSON))
    with patch.object(client._http, "get", mock_get):
        stats = await client.get_hero_stats()
    assert stats[1].pick_rate == pytest.approx(1.0)
    assert stats[5].pick_rate == pytest.approx(0.5)


async def test_get_hero_matchups(client):
    mock_get = AsyncMock(return_value=_make_mock_resp(MATCHUPS_JSON))
    with patch.object(client._http, "get", mock_get):
        matchups = await client.get_hero_matchups(1, ID_TO_SLUG)
    assert len(matchups) == 2
    cm = next(m for m in matchups if m.hero_slug == "crystal_maiden")
    assert cm.win_rate == pytest.approx(0.4)
    assert cm.advantage == pytest.approx(-0.1)
    mock_get.assert_called_once_with("https://api.opendota.com/api/heroes/1/matchups")


async def test_get_player_heroes(client):
    mock_get = AsyncMock(return_value=_make_mock_resp(PLAYER_HEROES_JSON))
    with patch.object(client._http, "get", mock_get):
        player_heroes = await client.get_player_heroes(123456789, ID_TO_SLUG)
    assert len(player_heroes) == 2
    am = next(h for h in player_heroes if h.hero_id == 1)
    assert am.games == 150
    assert am.wins == 82
    assert am.hero_slug == "antimage"
    assert am.win_rate == pytest.approx(82 / 150)


@pytest.mark.asyncio
async def test_get_player_stats(respx_mock):
    respx_mock.get("https://api.opendota.com/api/players/123").mock(
        return_value=httpx.Response(200, json={"win": 150, "lose": 100})
    )
    client = OpenDotaClient()
    stats = await client.get_player_stats(123)
    assert stats.wins == 150
    assert stats.losses == 100
    assert abs(stats.win_rate - 0.6) < 0.001
    await client.close()


@pytest.mark.asyncio
async def test_get_player_stats_ranked(respx_mock):
    respx_mock.get("https://api.opendota.com/api/players/123/wl").mock(
        return_value=httpx.Response(200, json={"win": 80, "lose": 50})
    )
    client = OpenDotaClient()
    stats = await client.get_player_stats_ranked(123)
    assert stats.wins == 80
    assert stats.losses == 50
    await client.close()
