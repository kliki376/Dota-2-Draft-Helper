import httpx
from dota_bot.models import HeroInfo, HeroMeta, HeroMatchup, PlayerHeroStats, PlayerStats, HeroMetaWithRole

BASE_URL = "https://api.opendota.com/api"
BRACKETS = [5, 6, 7, 8]


class OpenDotaClient:
    def __init__(self, api_key: str = ""):
        headers = {"Authorization": api_key} if api_key else {}
        self._http = httpx.AsyncClient(headers=headers, timeout=15.0)

    async def get_heroes(self) -> list[HeroInfo]:
        resp = await self._http.get(f"{BASE_URL}/heroes")
        resp.raise_for_status()
        return [
            HeroInfo(
                id=h["id"],
                slug=h["name"].replace("npc_dota_hero_", ""),
                localized_name=h["localized_name"],
            )
            for h in resp.json()
        ]

    async def get_hero_stats(self) -> dict[int, HeroMeta]:
        resp = await self._http.get(f"{BASE_URL}/heroStats")
        resp.raise_for_status()
        data = resp.json()
        all_games = [sum(h.get(f"{b}_pick", 0) for b in BRACKETS) for h in data]
        max_games = max(all_games, default=1)
        result: dict[int, HeroMeta] = {}
        for h, total_games in zip(data, all_games):
            total_wins = sum(h.get(f"{b}_win", 0) for b in BRACKETS)
            result[h["id"]] = HeroMeta(
                hero_id=h["id"],
                hero_slug=h["name"].replace("npc_dota_hero_", ""),
                win_rate=total_wins / total_games if total_games > 0 else 0.5,
                pick_rate=total_games / max_games,
                pro_pick=h.get("pro_pick", 0),
                pro_win=h.get("pro_win", 0),
            )
        return result

    async def get_hero_matchups(
        self, hero_id: int, id_to_slug: dict[int, str]
    ) -> list[HeroMatchup]:
        resp = await self._http.get(f"{BASE_URL}/heroes/{hero_id}/matchups")
        resp.raise_for_status()
        matchups = []
        for m in resp.json():
            if m["games_played"] == 0:
                continue
            wr = m["wins"] / m["games_played"]
            matchups.append(HeroMatchup(
                hero_slug=id_to_slug.get(m["hero_id"], str(m["hero_id"])),
                win_rate=wr,
                advantage=wr - 0.5,
            ))
        return matchups

    async def get_player_heroes(
        self, account_id: int, id_to_slug: dict[int, str]
    ) -> list[PlayerHeroStats]:
        resp = await self._http.get(f"{BASE_URL}/players/{account_id}/heroes")
        resp.raise_for_status()
        return [
            PlayerHeroStats(
                hero_id=h["hero_id"],
                hero_slug=id_to_slug.get(h["hero_id"], str(h["hero_id"])),
                games=h["games"],
                wins=h["win"],
            )
            for h in resp.json()
        ]

    async def get_hero_stats_with_role(self) -> dict[int, HeroMetaWithRole]:
        resp = await self._http.get(f"{BASE_URL}/heroStats")
        resp.raise_for_status()
        data = resp.json()
        all_games = [sum(h.get(f"{b}_pick", 0) for b in BRACKETS) for h in data]
        max_games = max(all_games, default=1)
        result: dict[int, HeroMetaWithRole] = {}
        for h, total_games in zip(data, all_games):
            total_wins = sum(h.get(f"{b}_win", 0) for b in BRACKETS)
            result[h["id"]] = HeroMetaWithRole(
                hero_id=h["id"],
                hero_slug=h["name"].replace("npc_dota_hero_", ""),
                win_rate=total_wins / total_games if total_games > 0 else 0.5,
                pick_rate=total_games / max_games,
                pro_pick=h.get("pro_pick", 0),
                pro_win=h.get("pro_win", 0),
                lane_role=h.get("lane_role", 0),
            )
        return result

    async def get_player_stats(self, account_id: int) -> PlayerStats:
        resp = await self._http.get(f"{BASE_URL}/players/{account_id}")
        resp.raise_for_status()
        data = resp.json()
        return PlayerStats(
            wins=data.get("win", 0),
            losses=data.get("lose", 0),
        )

    async def get_player_stats_ranked(self, account_id: int) -> PlayerStats:
        resp = await self._http.get(f"{BASE_URL}/players/{account_id}/wl", params={"lobby_type": 7})
        resp.raise_for_status()
        data = resp.json()
        return PlayerStats(
            wins=data.get("win", 0),
            losses=data.get("lose", 0),
        )

    async def close(self) -> None:
        await self._http.aclose()
