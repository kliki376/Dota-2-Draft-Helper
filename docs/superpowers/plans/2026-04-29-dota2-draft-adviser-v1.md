# Dota 2 Draft Adviser Bot v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that accepts enemy/ally heroes, fetches matchup/synergy/meta data from Dotabuff and OpenDota, and returns a top-5 pick recommendation with scores.

**Architecture:** Async Telegram bot (python-telegram-bot v20) with modular parsers. Dotabuff scraper handles matchup and duo data. OpenDota API provides meta winrates. A scoring engine weights Counter (40%), Synergy (25%), Meta (20%), Pro Pick (15%, neutral in v1.0) into a 0–100 score per candidate hero. A JSON file with TTL handles caching so Dotabuff is not hit on every request.

**Tech Stack:** Python 3.11+, python-telegram-bot 20.x, httpx, BeautifulSoup4, pytest, pytest-asyncio

---

## File Map

```
dota_bot/
├── config.py              — bot token, URLs, weights, cache TTL
├── models.py              — HeroMatchup, HeroDuo, HeroMeta, HeroScore dataclasses
├── hero_names.py          — slug ↔ display name mapping + alias resolution
├── cache.py               — JSON file cache with per-key TTL
├── opendota.py            — OpenDota API client (hero meta winrates)
├── parsers/
│   ├── __init__.py
│   └── dotabuff.py        — async scraper: matchups + duos
├── scorer.py              — scoring algorithm, cache-aware
├── formatter.py           — Telegram markdown formatter
└── bot.py                 — entry point: command handlers

tests/
├── conftest.py
├── test_hero_names.py
├── test_cache.py
├── test_opendota.py
├── test_scorer.py
├── test_formatter.py
├── test_bot.py
└── parsers/
    └── test_dotabuff.py
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `dota_bot/__init__.py`
- Create: `dota_bot/parsers/__init__.py`
- Create: `dota_bot/config.py`
- Create: `dota_bot/models.py`
- Create: `tests/__init__.py`
- Create: `tests/parsers/__init__.py`
- Create: `.env.example`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p dota_bot/parsers tests/parsers
touch dota_bot/__init__.py dota_bot/parsers/__init__.py tests/__init__.py tests/parsers/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
python-telegram-bot==20.7
httpx==0.27.0
beautifulsoup4==4.12.3
pytest==8.1.1
pytest-asyncio==0.23.6
python-dotenv==1.0.1
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 4: Create `.env.example`**

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

- [ ] **Step 5: Create `dota_bot/config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
CACHE_FILE = "dota_bot/cache.json"

DOTABUFF_BASE = "https://www.dotabuff.com/heroes"
OPENDOTA_API = "https://api.opendota.com/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    "counter": 0.40,
    "synergy": 0.25,
    "meta": 0.20,
    "pro": 0.15,
}
```

- [ ] **Step 6: Create `dota_bot/models.py`**

```python
from dataclasses import dataclass, field


@dataclass
class HeroMatchup:
    hero_slug: str
    advantage: float   # advantage % from Dotabuff (positive = we have the edge)
    win_rate: float    # winrate in this matchup (0.0–1.0)


@dataclass
class HeroDuo:
    hero_slug: str
    win_rate: float    # winrate when paired together (0.0–1.0)


@dataclass
class HeroMeta:
    hero_slug: str
    win_rate: float    # overall pub winrate in current patch (0.0–1.0)
    pick_rate: float   # normalized pick rate (0.0–1.0)


@dataclass
class HeroScore:
    hero_slug: str
    score: float                                   # 0–100
    counter_score: float
    synergy_score: float
    meta_score: float
    pro_score: float
    matchup_details: list[HeroMatchup] = field(default_factory=list)
    meta: HeroMeta | None = None
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt dota_bot/ tests/ .env.example
git commit -m "feat: project structure, config, and models"
```

---

## Task 2: Hero Names Module

Maps user-provided names ("Crystal Maiden", "cm", "anti mage") to Dotabuff slugs ("crystal-maiden", "anti-mage") and back to display names.

**Files:**
- Create: `dota_bot/hero_names.py`
- Create: `tests/test_hero_names.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_hero_names.py
from dota_bot.hero_names import to_slug, to_display_name, normalize_hero_list


def test_simple_name_to_slug():
    assert to_slug("Axe") == "axe"


def test_multiword_name_to_slug():
    assert to_slug("Crystal Maiden") == "crystal-maiden"


def test_alias_cm():
    assert to_slug("cm") == "crystal-maiden"


def test_alias_am():
    assert to_slug("am") == "anti-mage"


def test_alias_pa():
    assert to_slug("pa") == "phantom-assassin"


def test_case_insensitive():
    assert to_slug("INVOKER") == "invoker"


def test_unknown_returns_none():
    assert to_slug("not_a_hero") is None


def test_display_name():
    assert to_display_name("crystal-maiden") == "Crystal Maiden"


def test_normalize_list():
    result = normalize_hero_list(["axe", "cm", "invoker", "pa", "lion"])
    assert result == ["axe", "crystal-maiden", "invoker", "phantom-assassin", "lion"]


def test_normalize_ignores_unknown():
    result = normalize_hero_list(["axe", "not_a_hero"])
    assert result == ["axe"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_hero_names.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dota_bot.hero_names'`

- [ ] **Step 3: Create `dota_bot/hero_names.py`**

```python
# dota_bot/hero_names.py

# Maps slug → display name (all 124 Dota 2 heroes)
SLUG_TO_DISPLAY: dict[str, str] = {
    "abaddon": "Abaddon",
    "alchemist": "Alchemist",
    "ancient-apparition": "Ancient Apparition",
    "anti-mage": "Anti-Mage",
    "arc-warden": "Arc Warden",
    "axe": "Axe",
    "bane": "Bane",
    "batrider": "Batrider",
    "beastmaster": "Beastmaster",
    "bloodseeker": "Bloodseeker",
    "bounty-hunter": "Bounty Hunter",
    "brewmaster": "Brewmaster",
    "bristleback": "Bristleback",
    "broodmother": "Broodmother",
    "centaur-warrunner": "Centaur Warrunner",
    "chaos-knight": "Chaos Knight",
    "chen": "Chen",
    "clinkz": "Clinkz",
    "clockwerk": "Clockwerk",
    "crystal-maiden": "Crystal Maiden",
    "dark-seer": "Dark Seer",
    "dark-willow": "Dark Willow",
    "dawnbreaker": "Dawnbreaker",
    "dazzle": "Dazzle",
    "death-prophet": "Death Prophet",
    "disruptor": "Disruptor",
    "doom": "Doom",
    "dragon-knight": "Dragon Knight",
    "drow-ranger": "Drow Ranger",
    "earth-spirit": "Earth Spirit",
    "earthshaker": "Earthshaker",
    "elder-titan": "Elder Titan",
    "ember-spirit": "Ember Spirit",
    "enchantress": "Enchantress",
    "enigma": "Enigma",
    "faceless-void": "Faceless Void",
    "grimstroke": "Grimstroke",
    "gyrocopter": "Gyrocopter",
    "hoodwink": "Hoodwink",
    "huskar": "Huskar",
    "invoker": "Invoker",
    "io": "Io",
    "jakiro": "Jakiro",
    "juggernaut": "Juggernaut",
    "keeper-of-the-light": "Keeper of the Light",
    "kunkka": "Kunkka",
    "legion-commander": "Legion Commander",
    "leshrac": "Leshrac",
    "lich": "Lich",
    "lifestealer": "Lifestealer",
    "lina": "Lina",
    "lion": "Lion",
    "lone-druid": "Lone Druid",
    "luna": "Luna",
    "lycan": "Lycan",
    "magnus": "Magnus",
    "marci": "Marci",
    "mars": "Mars",
    "medusa": "Medusa",
    "meepo": "Meepo",
    "mirana": "Mirana",
    "monkey-king": "Monkey King",
    "morphling": "Morphling",
    "muerta": "Muerta",
    "naga-siren": "Naga Siren",
    "natures-prophet": "Nature's Prophet",
    "necrophos": "Necrophos",
    "night-stalker": "Night Stalker",
    "nyx-assassin": "Nyx Assassin",
    "ogre-magi": "Ogre Magi",
    "omniknight": "Omniknight",
    "oracle": "Oracle",
    "outworld-destroyer": "Outworld Destroyer",
    "pangolier": "Pangolier",
    "phantom-assassin": "Phantom Assassin",
    "phantom-lancer": "Phantom Lancer",
    "phoenix": "Phoenix",
    "primal-beast": "Primal Beast",
    "puck": "Puck",
    "pudge": "Pudge",
    "pugna": "Pugna",
    "queen-of-pain": "Queen of Pain",
    "razor": "Razor",
    "riki": "Riki",
    "rubick": "Rubick",
    "sand-king": "Sand King",
    "shadow-demon": "Shadow Demon",
    "shadow-fiend": "Shadow Fiend",
    "shadow-shaman": "Shadow Shaman",
    "silencer": "Silencer",
    "skywrath-mage": "Skywrath Mage",
    "slardar": "Slardar",
    "slark": "Slark",
    "snapfire": "Snapfire",
    "sniper": "Sniper",
    "spectre": "Spectre",
    "spirit-breaker": "Spirit Breaker",
    "storm-spirit": "Storm Spirit",
    "sven": "Sven",
    "techies": "Techies",
    "templar-assassin": "Templar Assassin",
    "terrorblade": "Terrorblade",
    "tidehunter": "Tidehunter",
    "timbersaw": "Timbersaw",
    "tinker": "Tinker",
    "tiny": "Tiny",
    "treant-protector": "Treant Protector",
    "troll-warlord": "Troll Warlord",
    "tusk": "Tusk",
    "underlord": "Underlord",
    "undying": "Undying",
    "ursa": "Ursa",
    "vengeful-spirit": "Vengeful Spirit",
    "venomancer": "Venomancer",
    "viper": "Viper",
    "visage": "Visage",
    "void-spirit": "Void Spirit",
    "warlock": "Warlock",
    "weaver": "Weaver",
    "windranger": "Windranger",
    "winter-wyvern": "Winter Wyvern",
    "witch-doctor": "Witch Doctor",
    "wraith-king": "Wraith King",
    "zeus": "Zeus",
}

# Common aliases → slug
ALIASES: dict[str, str] = {
    "aa": "ancient-apparition",
    "am": "anti-mage",
    "arc": "arc-warden",
    "bb": "bristleback",
    "bh": "bounty-hunter",
    "brew": "brewmaster",
    "cent": "centaur-warrunner",
    "ck": "chaos-knight",
    "cm": "crystal-maiden",
    "dk": "dragon-knight",
    "dp": "death-prophet",
    "dr": "drow-ranger",
    "ds": "dark-seer",
    "dw": "dark-willow",
    "es": "earth-spirit",
    "fv": "faceless-void",
    "void": "faceless-void",
    "gyro": "gyrocopter",
    "inv": "invoker",
    "jug": "juggernaut",
    "kotl": "keeper-of-the-light",
    "lc": "legion-commander",
    "lesh": "leshrac",
    "ls": "lifestealer",
    "mk": "monkey-king",
    "morph": "morphling",
    "np": "natures-prophet",
    "ns": "night-stalker",
    "nyx": "nyx-assassin",
    "od": "outworld-destroyer",
    "ogre": "ogre-magi",
    "pa": "phantom-assassin",
    "pango": "pangolier",
    "pl": "phantom-lancer",
    "qop": "queen-of-pain",
    "sb": "spirit-breaker",
    "sd": "shadow-demon",
    "sf": "shadow-fiend",
    "sk": "sand-king",
    "sl": "slark",
    "ss": "shadow-shaman",
    "ta": "templar-assassin",
    "tb": "terrorblade",
    "tide": "tidehunter",
    "timber": "timbersaw",
    "tp": "treant-protector",
    "troll": "troll-warlord",
    "veno": "venomancer",
    "void spirit": "void-spirit",
    "vs": "vengeful-spirit",
    "wd": "witch-doctor",
    "wk": "wraith-king",
    "wr": "windranger",
    "ww": "winter-wyvern",
}

# Reverse map: display name (lowercase) → slug
_DISPLAY_TO_SLUG: dict[str, str] = {v.lower(): k for k, v in SLUG_TO_DISPLAY.items()}


def to_slug(name: str) -> str | None:
    """Convert any user-provided hero name to a Dotabuff slug. Returns None if unknown."""
    normalized = name.strip().lower()
    if normalized in ALIASES:
        return ALIASES[normalized]
    if normalized in _DISPLAY_TO_SLUG:
        return _DISPLAY_TO_SLUG[normalized]
    slug_attempt = normalized.replace(" ", "-")
    if slug_attempt in SLUG_TO_DISPLAY:
        return slug_attempt
    return None


def to_display_name(slug: str) -> str:
    """Convert a Dotabuff slug to a human-readable display name."""
    return SLUG_TO_DISPLAY.get(slug, slug.replace("-", " ").title())


def normalize_hero_list(names: list[str]) -> list[str]:
    """Convert a list of user-provided names to slugs, silently dropping unknowns."""
    result = []
    for name in names:
        slug = to_slug(name)
        if slug is not None:
            result.append(slug)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_hero_names.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/hero_names.py tests/test_hero_names.py
git commit -m "feat: hero name normalization with alias support"
```

---

## Task 3: Cache Module

JSON file cache with per-key TTL. Keys expire independently.

**Files:**
- Create: `dota_bot/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cache.py
import time
import os
import pytest
from dota_bot.cache import Cache

TMP = "tests/tmp_cache_test.json"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists(TMP):
        os.remove(TMP)


def test_set_and_get():
    c = Cache(TMP, ttl_seconds=60)
    c.set("key1", {"data": 42})
    assert c.get("key1") == {"data": 42}


def test_missing_key_returns_none():
    c = Cache(TMP, ttl_seconds=60)
    assert c.get("nonexistent") is None


def test_expired_key_returns_none():
    c = Cache(TMP, ttl_seconds=0)
    c.set("key1", {"data": 42})
    time.sleep(0.01)
    assert c.get("key1") is None


def test_persists_across_instances():
    c1 = Cache(TMP, ttl_seconds=60)
    c1.set("hero", "axe")
    c2 = Cache(TMP, ttl_seconds=60)
    assert c2.get("hero") == "axe"


def test_invalidate_removes_key():
    c = Cache(TMP, ttl_seconds=60)
    c.set("key1", "value")
    c.invalidate("key1")
    assert c.get("key1") is None


def test_clear_removes_all():
    c = Cache(TMP, ttl_seconds=60)
    c.set("a", 1)
    c.set("b", 2)
    c.clear()
    assert c.get("a") is None
    assert c.get("b") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cache.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dota_bot.cache'`

- [ ] **Step 3: Implement `dota_bot/cache.py`**

```python
# dota_bot/cache.py
import json
import os
import time


class Cache:
    def __init__(self, path: str, ttl_seconds: int):
        self.path = path
        self.ttl = ttl_seconds
        self._data: dict = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f)

    def get(self, key: str):
        entry = self._data.get(key)
        if entry is None:
            return None
        if time.time() - entry["ts"] > self.ttl:
            del self._data[key]
            self._save()
            return None
        return entry["value"]

    def set(self, key: str, value) -> None:
        self._data[key] = {"ts": time.time(), "value": value}
        self._save()

    def invalidate(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._save()

    def clear(self) -> None:
        self._data = {}
        self._save()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cache.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/cache.py tests/test_cache.py
git commit -m "feat: TTL-based JSON cache"
```

---

## Task 4: OpenDota API Client

Fetches hero meta stats (pub winrate, pick rate) from the free OpenDota REST API. No scraping — pure JSON.

**Files:**
- Create: `dota_bot/opendota.py`
- Create: `tests/test_opendota.py`

OpenDota endpoint: `GET https://api.opendota.com/api/heroStats`

Response is a JSON array. Each element has:
- `localized_name`: display name ("Crystal Maiden")
- `pub_win`: total pub wins (integer)
- `pub_pick`: total pub picks (integer)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_opendota.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dota_bot.opendota import OpenDotaClient
from dota_bot.models import HeroMeta

FAKE_STATS = [
    {"localized_name": "Axe",            "pub_win": 550000, "pub_pick": 1000000},
    {"localized_name": "Crystal Maiden", "pub_win": 480000, "pub_pick": 1000000},
]


def make_mock(data):
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


@pytest.mark.asyncio
async def test_fetch_returns_dict_of_slugs():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=make_mock(FAKE_STATS)):
        result = await OpenDotaClient().fetch_hero_meta()
    assert "axe" in result
    assert "crystal-maiden" in result


@pytest.mark.asyncio
async def test_fetch_returns_herometa_instances():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=make_mock(FAKE_STATS)):
        result = await OpenDotaClient().fetch_hero_meta()
    assert isinstance(result["axe"], HeroMeta)


@pytest.mark.asyncio
async def test_winrate_is_correct():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=make_mock(FAKE_STATS)):
        result = await OpenDotaClient().fetch_hero_meta()
    assert abs(result["axe"].win_rate - 0.55) < 0.01
    assert abs(result["crystal-maiden"].win_rate - 0.48) < 0.01


@pytest.mark.asyncio
async def test_pick_rate_normalized_to_0_1():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=make_mock(FAKE_STATS)):
        result = await OpenDotaClient().fetch_hero_meta()
    for meta in result.values():
        assert 0.0 <= meta.pick_rate <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_opendota.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dota_bot.opendota'`

- [ ] **Step 3: Implement `dota_bot/opendota.py`**

```python
# dota_bot/opendota.py
import httpx
from dota_bot.config import OPENDOTA_API, HEADERS
from dota_bot.models import HeroMeta
from dota_bot.hero_names import to_slug


class OpenDotaClient:
    async def fetch_hero_meta(self) -> dict[str, HeroMeta]:
        """Returns slug → HeroMeta with pub winrate and normalized pick rate."""
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            resp = await client.get(f"{OPENDOTA_API}/heroStats")
            resp.raise_for_status()
            data = resp.json()

        result: dict[str, HeroMeta] = {}
        for hero in data:
            name = hero.get("localized_name", "")
            slug = to_slug(name)
            if slug is None:
                continue
            pub_win = hero.get("pub_win", 0)
            pub_pick = hero.get("pub_pick", 1)
            win_rate = pub_win / pub_pick if pub_pick > 0 else 0.5
            result[slug] = HeroMeta(
                hero_slug=slug,
                win_rate=win_rate,
                pick_rate=float(pub_pick),   # raw; normalized below
            )

        if result:
            max_pick = max(m.pick_rate for m in result.values())
            for m in result.values():
                m.pick_rate = m.pick_rate / max_pick if max_pick > 0 else 0.0

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_opendota.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/opendota.py tests/test_opendota.py
git commit -m "feat: OpenDota API client for hero meta winrates"
```

---

## Task 5: Dotabuff Parser — Matchups & Duos

Scrapes two Dotabuff pages for a given hero:
- `dotabuff.com/heroes/{slug}/matchups` → advantage % and winrate vs each enemy
- `dotabuff.com/heroes/{slug}/duos` → winrate when paired with each ally

Dotabuff table structure (both pages share the same layout):
```html
<table class="sortable">
  <tbody>
    <tr>
      <td class="cell-xlarge"><a href="/heroes/axe">Axe</a></td>
      <td>12345</td>                              <!-- games -->
      <td data-value="53.45">53.45%</td>          <!-- win rate -->
      <td data-value="2.31">+2.31%</td>           <!-- advantage (matchups only) -->
    </tr>
  </tbody>
</table>
```

**Files:**
- Create: `dota_bot/parsers/dotabuff.py`
- Create: `tests/parsers/test_dotabuff.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/parsers/test_dotabuff.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dota_bot.parsers.dotabuff import DotabuffParser
from dota_bot.models import HeroMatchup, HeroDuo

MATCHUP_HTML = """
<html><body><table class="sortable"><tbody>
<tr>
  <td class="cell-xlarge"><a href="/heroes/axe">Axe</a></td>
  <td>12345</td>
  <td data-value="53.45">53.45%</td>
  <td data-value="2.31">+2.31%</td>
</tr>
<tr>
  <td class="cell-xlarge"><a href="/heroes/lion">Lion</a></td>
  <td>9876</td>
  <td data-value="47.20">47.20%</td>
  <td data-value="-1.50">-1.50%</td>
</tr>
</tbody></table></body></html>
"""

DUO_HTML = """
<html><body><table class="sortable"><tbody>
<tr>
  <td class="cell-xlarge"><a href="/heroes/shadow-fiend">Shadow Fiend</a></td>
  <td>5432</td>
  <td data-value="57.10">57.10%</td>
</tr>
</tbody></table></body></html>
"""


def mock_resp(html: str):
    m = MagicMock()
    m.text = html
    m.raise_for_status = MagicMock()
    return m


@pytest.mark.asyncio
async def test_get_matchups_returns_list():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp(MATCHUP_HTML)):
        result = await DotabuffParser().get_matchups("silencer")
    assert len(result) == 2
    assert all(isinstance(m, HeroMatchup) for m in result)


@pytest.mark.asyncio
async def test_matchup_positive_advantage():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp(MATCHUP_HTML)):
        result = await DotabuffParser().get_matchups("silencer")
    axe = next(m for m in result if m.hero_slug == "axe")
    assert abs(axe.advantage - 2.31) < 0.01
    assert abs(axe.win_rate - 0.5345) < 0.001


@pytest.mark.asyncio
async def test_matchup_negative_advantage():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp(MATCHUP_HTML)):
        result = await DotabuffParser().get_matchups("silencer")
    lion = next(m for m in result if m.hero_slug == "lion")
    assert abs(lion.advantage - (-1.50)) < 0.01


@pytest.mark.asyncio
async def test_get_duos_returns_list():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp(DUO_HTML)):
        result = await DotabuffParser().get_duos("silencer")
    assert len(result) == 1
    assert isinstance(result[0], HeroDuo)
    assert result[0].hero_slug == "shadow-fiend"
    assert abs(result[0].win_rate - 0.5710) < 0.001
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/parsers/test_dotabuff.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dota_bot.parsers.dotabuff'`

- [ ] **Step 3: Implement `dota_bot/parsers/dotabuff.py`**

```python
# dota_bot/parsers/dotabuff.py
import asyncio
import httpx
from bs4 import BeautifulSoup
from dota_bot.config import DOTABUFF_BASE, HEADERS
from dota_bot.models import HeroMatchup, HeroDuo
from dota_bot.hero_names import to_slug


class DotabuffParser:
    async def _fetch(self, url: str) -> BeautifulSoup:
        await asyncio.sleep(0.5)   # polite delay to avoid rate-limiting
        async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    async def get_matchups(self, hero_slug: str) -> list[HeroMatchup]:
        """Scrape matchup advantage and winrate for every hero vs `hero_slug`."""
        soup = await self._fetch(f"{DOTABUFF_BASE}/{hero_slug}/matchups")
        results = []
        for row in soup.select("table.sortable tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            link = cells[0].find("a")
            if not link:
                continue
            raw_slug = link["href"].split("/heroes/")[-1]
            slug = to_slug(raw_slug) or raw_slug
            try:
                win_rate = float(cells[2].get("data-value", 0)) / 100
                advantage = float(cells[3].get("data-value", 0))
            except ValueError:
                continue
            results.append(HeroMatchup(hero_slug=slug, advantage=advantage, win_rate=win_rate))
        return results

    async def get_duos(self, hero_slug: str) -> list[HeroDuo]:
        """Scrape duo winrates — how well `hero_slug` pairs with each ally."""
        soup = await self._fetch(f"{DOTABUFF_BASE}/{hero_slug}/duos")
        results = []
        for row in soup.select("table.sortable tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            link = cells[0].find("a")
            if not link:
                continue
            raw_slug = link["href"].split("/heroes/")[-1]
            slug = to_slug(raw_slug) or raw_slug
            try:
                win_rate = float(cells[2].get("data-value", 0)) / 100
            except ValueError:
                continue
            results.append(HeroDuo(hero_slug=slug, win_rate=win_rate))
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/parsers/test_dotabuff.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/parsers/dotabuff.py tests/parsers/test_dotabuff.py
git commit -m "feat: Dotabuff parser for matchups and duos"
```

---

## Task 6: Scoring Engine

Computes a 0–100 score for each candidate hero given the enemy and ally lists.

**Scoring components:**
- **Counter Score** (40%): Fetch candidate's matchups from Dotabuff → average normalized advantage against the enemies. Advantage typically ranges −10 to +10%; map to 0–1.
- **Synergy Score** (25%): Fetch candidate's duos from Dotabuff → average normalized winrate with allies. Map 44–60% winrate range to 0–1.
- **Meta Score** (20%): Candidate's pub winrate from OpenDota. Map 44–60% range to 0–1.
- **Pro Score** (15%): Set to 0.5 (neutral) in v1.0 — Pro Tracker integration is v1.1.
- **Filter**: Exclude heroes with pub winrate < 48%.

Results are cached by hero slug to avoid re-scraping within the TTL window.

**Files:**
- Create: `dota_bot/scorer.py`
- Create: `tests/test_scorer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dota_bot.scorer import Scorer, normalize_advantage, normalize_winrate
from dota_bot.models import HeroMatchup, HeroDuo, HeroMeta, HeroScore


def test_normalize_advantage_positive():
    assert 0.7 < normalize_advantage(5.0) < 0.9


def test_normalize_advantage_negative():
    assert 0.1 < normalize_advantage(-5.0) < 0.4


def test_normalize_advantage_zero_is_neutral():
    assert abs(normalize_advantage(0.0) - 0.5) < 0.05


def test_normalize_winrate_above_50():
    assert normalize_winrate(0.55) > 0.5


def test_normalize_winrate_50_is_neutral():
    assert abs(normalize_winrate(0.50) - 0.5) < 0.1


@pytest.mark.asyncio
async def test_compute_scores_returns_heroscore_list():
    mock_matchups = [HeroMatchup("axe", 3.0, 0.53)]
    mock_meta = {"silencer": HeroMeta("silencer", 0.54, 0.8)}

    with patch("dota_bot.scorer.DotabuffParser") as MockParser, \
         patch("dota_bot.scorer.OpenDotaClient") as MockOD, \
         patch("dota_bot.scorer.Cache"):
        instance = MockParser.return_value
        instance.get_matchups = AsyncMock(return_value=mock_matchups)
        instance.get_duos = AsyncMock(return_value=[])
        MockOD.return_value.fetch_hero_meta = AsyncMock(return_value=mock_meta)

        results = await Scorer().compute_scores(
            enemies=["axe"], allies=[], candidate_slugs=["silencer"]
        )

    assert len(results) >= 1
    assert all(isinstance(r, HeroScore) for r in results)


@pytest.mark.asyncio
async def test_low_winrate_hero_excluded():
    mock_meta = {"pudge": HeroMeta("pudge", 0.46, 0.9)}  # below 48% threshold

    with patch("dota_bot.scorer.DotabuffParser") as MockParser, \
         patch("dota_bot.scorer.OpenDotaClient") as MockOD, \
         patch("dota_bot.scorer.Cache"):
        instance = MockParser.return_value
        instance.get_matchups = AsyncMock(return_value=[])
        instance.get_duos = AsyncMock(return_value=[])
        MockOD.return_value.fetch_hero_meta = AsyncMock(return_value=mock_meta)

        results = await Scorer().compute_scores(
            enemies=["axe"], allies=[], candidate_slugs=["pudge"]
        )

    assert all(r.hero_slug != "pudge" for r in results)


@pytest.mark.asyncio
async def test_results_sorted_by_score_descending():
    mock_meta = {
        "silencer": HeroMeta("silencer", 0.55, 0.8),
        "pugna": HeroMeta("pugna", 0.52, 0.7),
    }

    with patch("dota_bot.scorer.DotabuffParser") as MockParser, \
         patch("dota_bot.scorer.OpenDotaClient") as MockOD, \
         patch("dota_bot.scorer.Cache"):
        instance = MockParser.return_value
        instance.get_matchups = AsyncMock(return_value=[HeroMatchup("axe", 5.0, 0.56)])
        instance.get_duos = AsyncMock(return_value=[])
        MockOD.return_value.fetch_hero_meta = AsyncMock(return_value=mock_meta)

        results = await Scorer().compute_scores(
            enemies=["axe"], allies=[], candidate_slugs=["silencer", "pugna"]
        )

    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scorer.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dota_bot.scorer'`

- [ ] **Step 3: Implement `dota_bot/scorer.py`**

```python
# dota_bot/scorer.py
import asyncio
from dota_bot.models import HeroMatchup, HeroDuo, HeroMeta, HeroScore
from dota_bot.parsers.dotabuff import DotabuffParser
from dota_bot.opendota import OpenDotaClient
from dota_bot.cache import Cache
from dota_bot.config import WEIGHTS, CACHE_FILE, CACHE_TTL_SECONDS

MIN_WINRATE = 0.48
TOP_N = 5


def normalize_advantage(adv: float) -> float:
    """Map advantage % (−10..+10) → 0.0–1.0."""
    return max(0.0, min(1.0, (adv + 10) / 20))


def normalize_winrate(wr: float) -> float:
    """Map winrate (0.44..0.60) → 0.0–1.0."""
    return max(0.0, min(1.0, (wr - 0.44) / 0.16))


class Scorer:
    def __init__(self):
        self._parser = DotabuffParser()
        self._od = OpenDotaClient()
        self._cache = Cache(CACHE_FILE, CACHE_TTL_SECONDS)

    async def _get_matchups(self, slug: str) -> list[HeroMatchup]:
        key = f"matchups:{slug}"
        cached = self._cache.get(key)
        if cached is not None:
            return [HeroMatchup(**m) for m in cached]
        matchups = await self._parser.get_matchups(slug)
        self._cache.set(key, [{"hero_slug": m.hero_slug, "advantage": m.advantage, "win_rate": m.win_rate} for m in matchups])
        return matchups

    async def _get_duos(self, slug: str) -> list[HeroDuo]:
        key = f"duos:{slug}"
        cached = self._cache.get(key)
        if cached is not None:
            return [HeroDuo(**d) for d in cached]
        duos = await self._parser.get_duos(slug)
        self._cache.set(key, [{"hero_slug": d.hero_slug, "win_rate": d.win_rate} for d in duos])
        return duos

    async def _score_candidate(
        self,
        candidate: str,
        enemies: list[str],
        allies: list[str],
        meta: dict[str, HeroMeta],
    ) -> HeroScore | None:
        hero_meta = meta.get(candidate)
        if hero_meta and hero_meta.win_rate < MIN_WINRATE:
            return None

        matchups = await self._get_matchups(candidate)
        enemy_matchups = [m for m in matchups if m.hero_slug in enemies]
        counter = (
            sum(normalize_advantage(m.advantage) for m in enemy_matchups) / len(enemy_matchups)
            if enemy_matchups else 0.5
        )

        duos = await self._get_duos(candidate) if allies else []
        ally_duos = [d for d in duos if d.hero_slug in allies]
        synergy = (
            sum(normalize_winrate(d.win_rate) for d in ally_duos) / len(ally_duos)
            if ally_duos else 0.5
        )

        meta_score = normalize_winrate(hero_meta.win_rate) if hero_meta else 0.5
        pro_score = 0.5   # Pro Tracker integration deferred to v1.1

        total = (
            counter * WEIGHTS["counter"]
            + synergy * WEIGHTS["synergy"]
            + meta_score * WEIGHTS["meta"]
            + pro_score * WEIGHTS["pro"]
        )

        return HeroScore(
            hero_slug=candidate,
            score=round(total * 100, 1),
            counter_score=round(counter * 100, 1),
            synergy_score=round(synergy * 100, 1),
            meta_score=round(meta_score * 100, 1),
            pro_score=round(pro_score * 100, 1),
            matchup_details=enemy_matchups,
            meta=hero_meta,
        )

    async def compute_scores(
        self,
        enemies: list[str],
        allies: list[str],
        candidate_slugs: list[str],
    ) -> list[HeroScore]:
        meta = await self._od.fetch_hero_meta()
        tasks = [self._score_candidate(c, enemies, allies, meta) for c in candidate_slugs]
        results = await asyncio.gather(*tasks)
        scored = [r for r in results if r is not None]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:TOP_N]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scorer.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/scorer.py tests/test_scorer.py
git commit -m "feat: scoring engine with counter/synergy/meta weights and cache"
```

---

## Task 7: Response Formatter

Converts `list[HeroScore]` into a Telegram-ready Markdown string.

**Files:**
- Create: `dota_bot/formatter.py`
- Create: `tests/test_formatter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_formatter.py
from dota_bot.formatter import format_picks, format_help
from dota_bot.models import HeroScore, HeroMatchup, HeroMeta


def _score(slug: str, score: float) -> HeroScore:
    return HeroScore(
        hero_slug=slug,
        score=score,
        counter_score=60.0,
        synergy_score=55.0,
        meta_score=65.0,
        pro_score=50.0,
        matchup_details=[
            HeroMatchup("axe", 3.2, 0.54),
            HeroMatchup("lion", -1.0, 0.48),
        ],
        meta=HeroMeta(slug, 0.543, 0.7),
    )


def test_contains_hero_name():
    assert "Silencer" in format_picks([_score("silencer", 87.0)])


def test_contains_score():
    assert "87" in format_picks([_score("silencer", 87.0)])


def test_shows_rank_numbers():
    result = format_picks([_score("silencer", 87.0), _score("pugna", 82.0)])
    assert "1." in result
    assert "2." in result


def test_shows_meta_winrate():
    result = format_picks([_score("silencer", 87.0)])
    assert "54" in result   # 54.3% winrate


def test_shows_top_matchup():
    result = format_picks([_score("silencer", 87.0)])
    assert "Axe" in result   # top matchup by advantage


def test_empty_list_returns_not_found_message():
    result = format_picks([])
    assert len(result) > 0   # returns a message, not empty string
    assert "не найдено" in result.lower() or "not found" in result.lower() or "герои" in result.lower()


def test_format_help_contains_commands():
    result = format_help()
    assert "/pick" in result
    assert "/meta" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_formatter.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dota_bot.formatter'`

- [ ] **Step 3: Implement `dota_bot/formatter.py`**

```python
# dota_bot/formatter.py
from dota_bot.models import HeroScore
from dota_bot.hero_names import to_display_name

SEP = "━" * 20


def format_picks(scores: list[HeroScore]) -> str:
    if not scores:
        return "Герои не найдены. Проверь названия врагов и попробуй снова."

    lines = ["🎯 *Идеальный пик для вашей ситуации:*\n"]
    for i, s in enumerate(scores, 1):
        name = to_display_name(s.hero_slug)
        lines.append(SEP)
        lines.append(f"*{i}. {name}*  |  Score: {s.score}/100")
        lines.append(SEP)

        if s.matchup_details:
            top3 = sorted(s.matchup_details, key=lambda m: m.advantage, reverse=True)[:3]
            lines.append("⚔️  *Контрпики:*")
            for m in top3:
                sign = "+" if m.advantage >= 0 else ""
                lines.append(f"   • {to_display_name(m.hero_slug)} ({sign}{m.advantage:.1f}%)")

        if s.meta:
            wr_pct = round(s.meta.win_rate * 100, 1)
            lines.append(f"📊 *Мета:* WR {wr_pct}%")

        lines.append("")

    return "\n".join(lines)


def format_error(message: str) -> str:
    return f"❌ {message}"


def format_help() -> str:
    return (
        "🤖 *Dota 2 Draft Adviser*\n\n"
        "Команды:\n"
        "/pick — подобрать пик\n"
        "/meta — топ-10 меты\n"
        "/help — эта справка\n\n"
        "Формат ввода:\n"
        "`/pick Axe, Lion, CM, Invoker, PA`\n\n"
        "С союзниками:\n"
        "`Враги: Axe, Lion, CM, Invoker, PA`\n"
        "`Союзники: SF, Rubick`"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_formatter.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/formatter.py tests/test_formatter.py
git commit -m "feat: Telegram markdown formatter for pick results"
```

---

## Task 8: Telegram Bot — Entry Point

Wires all modules together. Handles `/pick`, `/meta`, `/start`, `/help`, `/refresh`.

`/pick` accepts heroes inline: `/pick Axe, Lion, CM, Invoker, PA`
or with the structured format:
```
Враги: Axe, Lion, CM, Invoker, PA
Союзники: SF, Rubick
```

`/meta` fetches OpenDota hero stats and displays the top-10 by winrate.

**Files:**
- Create: `dota_bot/bot.py`
- Create: `tests/test_bot.py`

- [ ] **Step 1: Write the failing tests**

Bot handler functions are async and require Telegram objects — we test only the pure input-parsing helper.

```python
# tests/test_bot.py
from dota_bot.bot import parse_pick_args


def test_plain_comma_list_as_enemies():
    enemies, allies = parse_pick_args("Axe, Lion, CM, Invoker, PA")
    assert "axe" in enemies
    assert "crystal-maiden" in enemies
    assert "phantom-assassin" in enemies
    assert allies == []


def test_structured_format_with_allies():
    enemies, allies = parse_pick_args("Враги: Axe, Lion\nСоюзники: SF, Rubick")
    assert "axe" in enemies
    assert "lion" in enemies
    assert "shadow-fiend" in allies
    assert "rubick" in allies


def test_compact_no_spaces():
    enemies, allies = parse_pick_args("axe,lion,invoker,pa,cm")
    assert len(enemies) == 5


def test_unknown_heroes_are_dropped():
    enemies, allies = parse_pick_args("Axe, NotAHero, Lion")
    assert "axe" in enemies
    assert "lion" in enemies
    assert len(enemies) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_bot.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'dota_bot.bot'`

- [ ] **Step 3: Implement `dota_bot/bot.py`**

```python
# dota_bot/bot.py
import asyncio
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dota_bot.config import BOT_TOKEN, CACHE_FILE, CACHE_TTL_SECONDS
from dota_bot.cache import Cache
from dota_bot.hero_names import normalize_hero_list, SLUG_TO_DISPLAY
from dota_bot.opendota import OpenDotaClient
from dota_bot.scorer import Scorer
from dota_bot.formatter import format_picks, format_error, format_help
from dota_bot.hero_names import to_display_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cache = Cache(CACHE_FILE, CACHE_TTL_SECONDS)
scorer = Scorer()
od_client = OpenDotaClient()


def parse_pick_args(text: str) -> tuple[list[str], list[str]]:
    """Parse enemy and ally hero names from free-form text. Returns (enemies, allies) as slug lists."""
    text = text.strip()
    enemy_match = re.search(r"(?:враги|enemies)[:\s]+([^\n]+)", text, re.IGNORECASE)
    ally_match = re.search(r"(?:союзники|allies)[:\s]+([^\n]+)", text, re.IGNORECASE)

    if enemy_match:
        enemies_raw = [h.strip() for h in enemy_match.group(1).split(",")]
    else:
        enemies_raw = [h.strip() for h in re.split(r"[,\n]+", text) if h.strip()]

    allies_raw = [h.strip() for h in ally_match.group(1).split(",")] if ally_match else []

    return normalize_hero_list(enemies_raw), normalize_hero_list(allies_raw)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_help(), parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_help(), parse_mode="Markdown")


async def cmd_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Введи героев врага после команды:\n`/pick Axe, Lion, CM, Invoker, PA`",
            parse_mode="Markdown",
        )
        return

    enemies, allies = parse_pick_args(text)
    if not enemies:
        await update.message.reply_text(
            format_error("Не распознал героев. Проверь названия и попробуй снова.")
        )
        return

    await update.message.reply_text("⏳ Анализирую драфт...")

    blocked = set(enemies) | set(allies)
    candidates = [s for s in SLUG_TO_DISPLAY if s not in blocked]

    try:
        scores = await scorer.compute_scores(enemies=enemies, allies=allies, candidate_slugs=candidates)
        await update.message.reply_text(format_picks(scores), parse_mode="Markdown")
    except Exception as e:
        logger.exception("Scoring failed: %s", e)
        await update.message.reply_text(format_error("Ошибка при анализе. Попробуй позже."))


async def cmd_meta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Загружаю мету...")
    try:
        meta = await od_client.fetch_hero_meta()
        top10 = sorted(meta.values(), key=lambda m: m.win_rate, reverse=True)[:10]
        lines = ["📊 *Топ-10 героев текущей меты:*\n"]
        for i, m in enumerate(top10, 1):
            wr = round(m.win_rate * 100, 1)
            lines.append(f"{i}. *{to_display_name(m.hero_slug)}* — {wr}% WR")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.exception("Meta fetch failed: %s", e)
        await update.message.reply_text(format_error("Не удалось загрузить мету."))


async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cache.clear()
    await update.message.reply_text("✅ Кэш очищен.")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pick", cmd_pick))
    app.add_handler(CommandHandler("meta", cmd_meta))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_bot.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests across all modules PASS

- [ ] **Step 6: Smoke-test the bot manually**

Create a `.env` file (not committed):
```
TELEGRAM_BOT_TOKEN=your_actual_token
```

Run the bot:
```bash
python -m dota_bot.bot
```

Open Telegram, find your bot, and run:
```
/pick Axe, Lion, Crystal Maiden, Invoker, Phantom Assassin
```

Expected: bot replies with top-5 picks, scores, and matchup details within ~30 seconds (first run scrapes Dotabuff; subsequent runs use cache).

- [ ] **Step 7: Commit**

```bash
git add dota_bot/bot.py tests/test_bot.py
git commit -m "feat: Telegram bot with /pick /meta /help /refresh — v1.0 complete"
```

---

## Self-Review Notes

**Spec coverage:**
- ✅ /start, /help, /pick, /meta, /refresh commands
- ✅ Dotabuff matchups + duos parser
- ✅ OpenDota meta winrates
- ✅ Counter (40%) + Synergy (25%) + Meta (20%) + Pro (15%) scoring
- ✅ Heroes with winrate < 48% filtered out
- ✅ Cache with 6-hour TTL
- ✅ Hero name aliases (cm, am, pa, etc.)
- ✅ Top-5 results with matchup details in Telegram markdown
- ⏭️  /hero command — deferred to v1.1 (not in v1.0 scope per roadmap)
- ⏭️  Player profile (/profile) — deferred to v1.2 per roadmap
- ⏭️  Pro Tracker scraper — deferred to v1.1 per roadmap

**Type consistency verified:**
- `DotabuffParser.get_matchups` → `list[HeroMatchup]` ✅
- `DotabuffParser.get_duos` → `list[HeroDuo]` ✅
- `OpenDotaClient.fetch_hero_meta` → `dict[str, HeroMeta]` ✅
- `Scorer.compute_scores` → `list[HeroScore]` ✅
- `HeroMatchup(**m)` reconstruction from cache uses exact field names ✅
