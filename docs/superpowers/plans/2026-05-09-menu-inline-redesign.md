# Menu Inline Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Переработать кнопки Мета, Герой и Профиль — все три открывают inline-клавиатуру вместо текстового ответа.

**Architecture:** Мета добавляет выбор позиции (1-5) перед показом топа героев. Герой использует тот же алфавитный picker что Пик, но с отдельными callback prefix'ами (`hero_info:*`). Профиль показывает разные клавиатуры в зависимости от наличия привязанного Steam ID, с полным набором функций статистики.

**Tech Stack:** Python 3.11, python-telegram-bot 20.7, httpx, OpenDota API

---

## File Map

- **Modify:** `dota_bot/keyboards.py` — добавить `meta_position_keyboard()`, `profile_keyboard_unlinked()`, `profile_keyboard_linked()`, `howto_keyboard()`, `hero_info_group_keyboard()`, `hero_info_hero_keyboard()`
- **Modify:** `dota_bot/formatter.py` — добавить `format_meta_by_position()`, `format_player_stats()`, `format_top_heroes()`
- **Modify:** `dota_bot/parsers/opendota_api.py` — добавить `get_player_stats()`, `get_player_stats_ranked()`
- **Modify:** `dota_bot/models.py` — добавить `PlayerStats`, `HeroMetaWithRole`
- **Modify:** `dota_bot/bot.py` — добавить `callback_meta()`, `callback_hero_info()`, `callback_profile()`, обновить `handle_menu_button()` и регистрацию хендлеров
- **Modify:** `tests/test_formatter.py` — добавить тесты новых форматтеров
- **Modify:** `tests/test_keyboards.py` — добавить тесты новых клавиатур

---

### Task 1: Новые модели данных

**Files:**
- Modify: `dota_bot/models.py`

- [ ] **Step 1: Добавить модели PlayerStats и HeroMetaWithRole**

Открыть `dota_bot/models.py` и добавить в конец файла:

```python
@dataclass
class PlayerStats:
    wins: int
    losses: int
    kda: float = 0.0

    @property
    def games(self) -> int:
        return self.wins + self.losses

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games > 0 else 0.0


@dataclass
class HeroMetaWithRole(HeroMeta):
    lane_role: int = 0  # 1=Carry, 2=Mid, 3=Offlane, 4=Soft Support, 5=Hard Support
```

- [ ] **Step 2: Commit**

```bash
git add dota_bot/models.py
git commit -m "feat: add PlayerStats and HeroMetaWithRole models"
```

---

### Task 2: OpenDota API — получение статистики игрока

**Files:**
- Modify: `dota_bot/parsers/opendota_api.py`
- Test: `tests/parsers/test_opendota_api.py`

- [ ] **Step 1: Написать падающий тест**

Открыть `tests/parsers/test_opendota_api.py` и добавить в конец:

```python
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
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/parsers/test_opendota_api.py::test_get_player_stats tests/parsers/test_opendota_api.py::test_get_player_stats_ranked -v
```

Ожидаем: FAIL — `AttributeError: 'OpenDotaClient' object has no attribute 'get_player_stats'`

- [ ] **Step 3: Реализовать методы в OpenDotaClient**

Открыть `dota_bot/parsers/opendota_api.py`, добавить импорт модели и два метода перед `close()`:

```python
from dota_bot.models import HeroInfo, HeroMeta, HeroMatchup, PlayerHeroStats, PlayerStats

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
```

- [ ] **Step 4: Запустить тест — убедиться что проходит**

```bash
pytest tests/parsers/test_opendota_api.py::test_get_player_stats tests/parsers/test_opendota_api.py::test_get_player_stats_ranked -v
```

Ожидаем: PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/parsers/opendota_api.py tests/parsers/test_opendota_api.py
git commit -m "feat: add get_player_stats and get_player_stats_ranked to OpenDotaClient"
```

---

### Task 3: OpenDota API — hero stats с lane_role

**Files:**
- Modify: `dota_bot/parsers/opendota_api.py`
- Test: `tests/parsers/test_opendota_api.py`

- [ ] **Step 1: Написать падающий тест**

Добавить в `tests/parsers/test_opendota_api.py`:

```python
@pytest.mark.asyncio
async def test_get_hero_stats_with_role(respx_mock):
    respx_mock.get("https://api.opendota.com/api/heroStats").mock(
        return_value=httpx.Response(200, json=[
            {
                "id": 1, "name": "npc_dota_hero_antimage", "localized_name": "Anti-Mage",
                "5_pick": 100, "5_win": 55, "6_pick": 50, "6_win": 28,
                "7_pick": 80, "7_win": 44, "8_pick": 30, "8_win": 16,
                "pro_pick": 10, "pro_win": 6, "1_pick": 200, "lane_role": 1,
            }
        ])
    )
    client = OpenDotaClient()
    stats = await client.get_hero_stats_with_role()
    assert 1 in stats
    assert stats[1].lane_role == 1
    assert stats[1].hero_slug == "antimage"
    await client.close()
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/parsers/test_opendota_api.py::test_get_hero_stats_with_role -v
```

Ожидаем: FAIL — `AttributeError: 'OpenDotaClient' object has no attribute 'get_hero_stats_with_role'`

- [ ] **Step 3: Реализовать метод**

Добавить в `dota_bot/parsers/opendota_api.py` после `get_hero_stats()`:

```python
    async def get_hero_stats_with_role(self) -> dict[int, "HeroMetaWithRole"]:
        from dota_bot.models import HeroMetaWithRole
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
```

- [ ] **Step 4: Запустить тест — убедиться что проходит**

```bash
pytest tests/parsers/test_opendota_api.py::test_get_hero_stats_with_role -v
```

Ожидаем: PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/parsers/opendota_api.py tests/parsers/test_opendota_api.py
git commit -m "feat: add get_hero_stats_with_role to OpenDotaClient"
```

---

### Task 4: Новые клавиатуры

**Files:**
- Modify: `dota_bot/keyboards.py`
- Test: `tests/test_keyboards.py`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `tests/test_keyboards.py`:

```python
from dota_bot.keyboards import (
    meta_position_keyboard, profile_keyboard_unlinked,
    profile_keyboard_linked, howto_keyboard,
    hero_info_group_keyboard, hero_info_hero_keyboard,
)
from dota_bot.models import HeroInfo


def test_meta_position_keyboard():
    kb = meta_position_keyboard()
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "meta:pos:1" in all_data
    assert "meta:pos:5" in all_data
    assert "meta:cancel" in all_data


def test_profile_keyboard_unlinked():
    kb = profile_keyboard_unlinked()
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "profile:link" in all_data
    assert "profile:close" in all_data


def test_profile_keyboard_linked():
    kb = profile_keyboard_linked()
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "profile:top_heroes" in all_data
    assert "profile:stats:all" in all_data
    assert "profile:stats:ranked" in all_data
    assert "profile:unlink" in all_data
    assert "profile:back" in all_data


def test_howto_keyboard():
    kb = howto_keyboard()
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "profile:howto:steam" in all_data
    assert "profile:howto:dotabuff" in all_data


def test_hero_info_group_keyboard():
    kb = hero_info_group_keyboard()
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert any(d.startswith("hero_info:group:") for d in all_data)
    assert "hero_info:cancel" in all_data


def test_hero_info_hero_keyboard():
    heroes = [HeroInfo(id=1, slug="antimage", localized_name="Anti-Mage")]
    kb = hero_info_hero_keyboard(heroes)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "hero_info:hero:antimage" in all_data
    assert "hero_info:back" in all_data
```

- [ ] **Step 2: Запустить тесты — убедиться что падают**

```bash
pytest tests/test_keyboards.py::test_meta_position_keyboard tests/test_keyboards.py::test_profile_keyboard_unlinked tests/test_keyboards.py::test_profile_keyboard_linked tests/test_keyboards.py::test_howto_keyboard tests/test_keyboards.py::test_hero_info_group_keyboard tests/test_keyboards.py::test_hero_info_hero_keyboard -v
```

Ожидаем: FAIL — ImportError

- [ ] **Step 3: Реализовать новые клавиатуры**

Добавить в конец `dota_bot/keyboards.py`:

```python
POSITIONS = [
    ("1️⃣ Carry", "meta:pos:1"),
    ("2️⃣ Mid", "meta:pos:2"),
    ("3️⃣ Offlane", "meta:pos:3"),
    ("4️⃣ Soft Support", "meta:pos:4"),
    ("5️⃣ Hard Support", "meta:pos:5"),
]


def meta_position_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(POSITIONS[0][0], callback_data=POSITIONS[0][1]),
         InlineKeyboardButton(POSITIONS[1][0], callback_data=POSITIONS[1][1]),
         InlineKeyboardButton(POSITIONS[2][0], callback_data=POSITIONS[2][1])],
        [InlineKeyboardButton(POSITIONS[3][0], callback_data=POSITIONS[3][1]),
         InlineKeyboardButton(POSITIONS[4][0], callback_data=POSITIONS[4][1])],
        [InlineKeyboardButton("✖ Отмена", callback_data="meta:cancel")],
    ])


def profile_keyboard_unlinked() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Привязать Steam ID", callback_data="profile:link")],
        [InlineKeyboardButton("✖ Закрыть", callback_data="profile:close")],
    ])


def profile_keyboard_linked() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏅 Лучшие герои", callback_data="profile:top_heroes")],
        [InlineKeyboardButton("🎮 Все игры", callback_data="profile:stats:all"),
         InlineKeyboardButton("🏆 Рейтинговые", callback_data="profile:stats:ranked")],
        [InlineKeyboardButton("❌ Отвязать", callback_data="profile:unlink"),
         InlineKeyboardButton("← Назад", callback_data="profile:back")],
    ])


def howto_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Через Steam", callback_data="profile:howto:steam"),
         InlineKeyboardButton("⚔️ Через Dotabuff", callback_data="profile:howto:dotabuff")],
    ])


def hero_info_group_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(label, callback_data=f"hero_info:group:{label}")
            for label, _ in LETTER_GROUPS[:4]
        ],
        [
            InlineKeyboardButton(label, callback_data=f"hero_info:group:{label}")
            for label, _ in LETTER_GROUPS[4:]
        ],
        [InlineKeyboardButton("✖ Отмена", callback_data="hero_info:cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def hero_info_hero_keyboard(heroes: list[HeroInfo]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(h.localized_name, callback_data=f"hero_info:hero:{h.slug}")
        for h in heroes
    ]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton("← Назад", callback_data="hero_info:back")])
    return InlineKeyboardMarkup(rows)
```

- [ ] **Step 4: Запустить тесты — убедиться что проходят**

```bash
pytest tests/test_keyboards.py -v
```

Ожидаем: все PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/keyboards.py tests/test_keyboards.py
git commit -m "feat: add meta/hero_info/profile inline keyboards"
```

---

### Task 5: Новые форматтеры

**Files:**
- Modify: `dota_bot/formatter.py`
- Test: `tests/test_formatter.py`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `tests/test_formatter.py`:

```python
from dota_bot.formatter import format_meta_by_position, format_player_stats, format_top_heroes
from dota_bot.models import HeroInfo, HeroMetaWithRole, PlayerStats, PlayerHeroStats


def test_format_meta_by_position():
    info = HeroInfo(id=1, slug="antimage", localized_name="Anti-Mage")
    meta = HeroMetaWithRole(
        hero_id=1, hero_slug="antimage", win_rate=0.54,
        pick_rate=0.8, pro_pick=50, pro_win=28, lane_role=1,
    )
    result = format_meta_by_position([(info, meta)], position=1)
    assert "Anti-Mage" in result
    assert "54" in result
    assert "Carry" in result


def test_format_player_stats():
    stats = PlayerStats(wins=100, losses=80)
    result = format_player_stats(stats, label="Все игры")
    assert "180" in result  # total games
    assert "55" in result   # winrate 100/180 = 55.5%
    assert "Все игры" in result


def test_format_top_heroes():
    heroes = [
        PlayerHeroStats(hero_id=1, hero_slug="antimage", games=50, wins=30),
    ]
    hero_info_map = {1: HeroInfo(id=1, slug="antimage", localized_name="Anti-Mage")}
    result = format_top_heroes(heroes, hero_info_map)
    assert "Anti-Mage" in result
    assert "50" in result
    assert "60" in result  # win_rate 30/50 = 60%
```

- [ ] **Step 2: Запустить тесты — убедиться что падают**

```bash
pytest tests/test_formatter.py::test_format_meta_by_position tests/test_formatter.py::test_format_player_stats tests/test_formatter.py::test_format_top_heroes -v
```

Ожидаем: FAIL — ImportError

- [ ] **Step 3: Реализовать форматтеры**

Добавить в конец `dota_bot/formatter.py`:

```python
from dota_bot.models import HeroScore, HeroInfo, HeroMeta, HeroMetaWithRole, PlayerStats, PlayerHeroStats

POSITION_NAMES = {1: "Carry", 2: "Mid", 3: "Offlane", 4: "Soft Support", 5: "Hard Support"}


def format_meta_by_position(
    hero_metas: list[tuple[HeroInfo, HeroMetaWithRole]],
    position: int,
) -> str:
    pos_name = POSITION_NAMES.get(position, str(position))
    if not hero_metas:
        return f"Нет данных о мете для позиции {pos_name}."
    lines = [f"📈 Топ героев — {pos_name}:\n"]
    for i, (info, meta) in enumerate(hero_metas, 1):
        pro_wr = (
            f"{meta.pro_win / meta.pro_pick * 100:.0f}%"
            if meta.pro_pick >= 20
            else "—"
        )
        lines.append(
            f"{i}. {info.localized_name} — WR {meta.win_rate * 100:.1f}% | Про: {pro_wr}"
        )
    return "\n".join(lines)


def format_player_stats(stats: PlayerStats, label: str) -> str:
    wr = stats.win_rate * 100
    return (
        f"📊 {label}\n\n"
        f"Игр: {stats.games}\n"
        f"Побед: {stats.wins} | Поражений: {stats.losses}\n"
        f"Winrate: {wr:.1f}%"
    )


def format_top_heroes(
    heroes: list[PlayerHeroStats],
    hero_info_map: dict[int, HeroInfo],
) -> str:
    if not heroes:
        return "Нет данных об играх."
    lines = ["🏅 Лучшие герои:\n"]
    for i, h in enumerate(heroes[:5], 1):
        info = hero_info_map.get(h.hero_id)
        name = info.localized_name if info else h.hero_slug
        wr = h.win_rate * 100
        lines.append(f"{i}. {name} — {h.games} игр | WR {wr:.0f}%")
    return "\n".join(lines)
```

Также обновить строку импорта в начале `formatter.py`:

```python
from dota_bot.models import HeroScore, HeroInfo, HeroMeta, HeroMetaWithRole, PlayerStats, PlayerHeroStats
```

- [ ] **Step 4: Запустить тесты — убедиться что проходят**

```bash
pytest tests/test_formatter.py -v
```

Ожидаем: все PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/formatter.py tests/test_formatter.py
git commit -m "feat: add format_meta_by_position, format_player_stats, format_top_heroes"
```

---

### Task 6: callback_meta — выбор позиции и топ меты

**Files:**
- Modify: `dota_bot/bot.py`

- [ ] **Step 1: Обновить импорты в bot.py**

В начале `dota_bot/bot.py` обновить строки импортов:

```python
from dota_bot.formatter import format_meta, format_picks, format_meta_by_position, format_player_stats, format_top_heroes
from dota_bot.keyboards import (
    group_keyboard, hero_keyboard, heroes_for_group, main_keyboard,
    meta_position_keyboard, profile_keyboard_unlinked, profile_keyboard_linked,
    howto_keyboard, hero_info_group_keyboard, hero_info_hero_keyboard,
)
from dota_bot.models import HeroInfo, HeroMatchup, HeroMeta, HeroMetaWithRole, PlayerHeroStats, PlayerStats
```

- [ ] **Step 2: Обновить handle_menu_button**

Найти функцию `handle_menu_button` и заменить её на:

```python
async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text == "🎯 Пик":
        await cmd_pick(update, context)
    elif text == "📈 Мета":
        await update.message.reply_text(
            "📈 Выберите позицию:",
            reply_markup=meta_position_keyboard(),
        )
    elif text == "🦸 Герой":
        await update.message.reply_text(
            "🦸 Выберите первую букву имени героя:",
            reply_markup=hero_info_group_keyboard(),
        )
    elif text == "👤 Профиль":
        account_id = _profiles.get(update.effective_user.id)
        if account_id:
            await update.message.reply_text(
                f"👤 Профиль привязан: Steam ID {account_id}",
                reply_markup=profile_keyboard_linked(),
            )
        else:
            await update.message.reply_text(
                "👤 Профиль не привязан.",
                reply_markup=profile_keyboard_unlinked(),
            )
```

- [ ] **Step 3: Добавить callback_meta**

Добавить новую функцию после `handle_menu_button`:

```python
async def callback_meta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "meta:cancel":
        await query.edit_message_text("❌ Отменено.")
        return

    if data.startswith("meta:pos:"):
        position = int(data[-1])
        await query.edit_message_text("⏳ Загружаю данные меты...")
        try:
            hero_stats = await _client.get_hero_stats_with_role()
            hero_info_map = {h.id: h for h in _all_heroes}
            filtered = sorted(
                [
                    (hero_info_map[hid], meta)
                    for hid, meta in hero_stats.items()
                    if hid in hero_info_map
                    and meta.lane_role == position
                    and meta.pick_rate > 0.02
                ],
                key=lambda x: x[1].win_rate,
                reverse=True,
            )[:10]
            await query.edit_message_text(format_meta_by_position(filtered, position))
        except Exception:
            logger.exception("Error in callback_meta")
            await query.edit_message_text("❌ Ошибка при загрузке данных.")
```

- [ ] **Step 4: Зарегистрировать хендлер в main()**

В функции `main()` добавить после регистрации `callback_pick`:

```python
    app.add_handler(CallbackQueryHandler(
        callback_meta,
        pattern=r"^meta:(pos:[1-5]|cancel)$",
    ))
```

- [ ] **Step 5: Commit**

```bash
git add dota_bot/bot.py
git commit -m "feat: add meta position selector with inline keyboard"
```

---

### Task 7: callback_hero_info — выбор героя и его статистика

**Files:**
- Modify: `dota_bot/bot.py`

- [ ] **Step 1: Добавить callback_hero_info**

Добавить в `dota_bot/bot.py` после `callback_meta`:

```python
async def callback_hero_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "hero_info:cancel":
        await query.edit_message_text("❌ Отменено.")
        return

    if data == "hero_info:back":
        await query.edit_message_text(
            "🦸 Выберите первую букву имени героя:",
            reply_markup=hero_info_group_keyboard(),
        )
        return

    if data.startswith("hero_info:group:"):
        group = data[len("hero_info:group:"):]
        heroes = heroes_for_group(_all_heroes, group)
        await query.edit_message_text(
            "🦸 Выберите героя:",
            reply_markup=hero_info_hero_keyboard(heroes),
        )
        return

    if data.startswith("hero_info:hero:"):
        slug = data[len("hero_info:hero:"):]
        hero = next((h for h in _all_heroes if h.slug == slug), None)
        if hero is None:
            await query.edit_message_text("❌ Герой не найден.")
            return
        try:
            hero_stats = await _fetch_hero_stats()
            meta = hero_stats.get(hero.id)
            if not meta:
                await query.edit_message_text("Нет данных по этому герою.")
                return
            pro_wr = (
                f"{meta.pro_win / meta.pro_pick * 100:.0f}%"
                if meta.pro_pick >= 20
                else "мало данных"
            )
            await query.edit_message_text(
                f"🦸 {hero.localized_name}\n\n"
                f"📊 Winrate: {meta.win_rate * 100:.1f}%\n"
                f"🏆 Про WR: {pro_wr} ({meta.pro_pick} пиков)\n"
                f"📈 Популярность: {meta.pick_rate * 100:.0f}%",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("← Назад", callback_data="hero_info:back")]
                ]),
            )
        except Exception:
            logger.exception("Error in callback_hero_info")
            await query.edit_message_text("❌ Ошибка при загрузке данных.")
```

- [ ] **Step 2: Зарегистрировать хендлер в main()**

В функции `main()` добавить:

```python
    app.add_handler(CallbackQueryHandler(
        callback_hero_info,
        pattern=r"^hero_info:(group:[A-Z-]+|hero:[a-z0-9_]+|back|cancel)$",
    ))
```

- [ ] **Step 3: Commit**

```bash
git add dota_bot/bot.py
git commit -m "feat: add hero info inline picker"
```

---

### Task 8: callback_profile — полный профиль с inline-клавиатурой

**Files:**
- Modify: `dota_bot/bot.py`

- [ ] **Step 1: Добавить callback_profile**

Добавить в `dota_bot/bot.py` после `callback_hero_info`:

```python
async def callback_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "profile:close" or data == "profile:back":
        await query.edit_message_text("👤 Закрыто.")
        return

    if data == "profile:link":
        context.user_data["awaiting_steam_id"] = True
        await query.edit_message_text(
            "Отправьте ваш Steam ID числом в чат.\n\n"
            "Не знаете где найти?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Как найти ID?", callback_data="profile:howto")]
            ]),
        )
        return

    if data == "profile:howto":
        await query.edit_message_text(
            "Как найти Steam ID?\n\nВыберите способ:",
            reply_markup=howto_keyboard(),
        )
        return

    if data == "profile:howto:steam":
        context.user_data["awaiting_steam_id"] = True
        await query.edit_message_text(
            "🎮 Через Steam:\n\n"
            "1. Зайдите на https://steamid.io\n"
            "2. Вставьте ссылку на ваш профиль Steam\n"
            "3. Сайт покажет ваш Steam ID (32-bit)\n\n"
            "Скопируйте число и отправьте мне:"
        )
        return

    if data == "profile:howto:dotabuff":
        context.user_data["awaiting_steam_id"] = True
        await query.edit_message_text(
            "⚔️ Через Dotabuff:\n\n"
            "1. Зайдите на https://www.dotabuff.com\n"
            "2. Найдите свой профиль\n"
            "3. Число в URL — это ваш ID:\n"
            "   dotabuff.com/players/123456789\n"
            "                        ↑ вот это\n\n"
            "Скопируйте число и отправьте мне:"
        )
        return

    if data == "profile:unlink":
        _profiles.remove(user_id)
        await query.edit_message_text(
            "✅ Профиль отвязан.",
            reply_markup=profile_keyboard_unlinked(),
        )
        return

    account_id = _profiles.get(user_id)
    if not account_id:
        await query.edit_message_text(
            "👤 Профиль не привязан.",
            reply_markup=profile_keyboard_unlinked(),
        )
        return

    if data == "profile:top_heroes":
        await query.edit_message_text("⏳ Загружаю...")
        try:
            id_to_slug = {h.id: h.slug for h in _all_heroes}
            heroes = await _client.get_player_heroes(account_id, id_to_slug)
            top = sorted(heroes, key=lambda h: h.games, reverse=True)[:5]
            hero_info_map = {h.id: h for h in _all_heroes}
            text = format_top_heroes(top, hero_info_map)
            await query.edit_message_text(text, reply_markup=profile_keyboard_linked())
        except Exception:
            logger.exception("Error in profile:top_heroes")
            await query.edit_message_text("❌ Ошибка при загрузке данных.", reply_markup=profile_keyboard_linked())
        return

    if data == "profile:stats:all":
        await query.edit_message_text("⏳ Загружаю...")
        try:
            stats = await _client.get_player_stats(account_id)
            text = format_player_stats(stats, label="Все игры")
            await query.edit_message_text(text, reply_markup=profile_keyboard_linked())
        except Exception:
            logger.exception("Error in profile:stats:all")
            await query.edit_message_text("❌ Ошибка при загрузке данных.", reply_markup=profile_keyboard_linked())
        return

    if data == "profile:stats:ranked":
        await query.edit_message_text("⏳ Загружаю...")
        try:
            stats = await _client.get_player_stats_ranked(account_id)
            text = format_player_stats(stats, label="Рейтинговые игры")
            await query.edit_message_text(text, reply_markup=profile_keyboard_linked())
        except Exception:
            logger.exception("Error in profile:stats:ranked")
            await query.edit_message_text("❌ Ошибка при загрузке данных.", reply_markup=profile_keyboard_linked())
        return
```

- [ ] **Step 2: Зарегистрировать хендлер в main()**

В функции `main()` добавить:

```python
    app.add_handler(CallbackQueryHandler(
        callback_profile,
        pattern=r"^profile:(link|close|back|howto|howto:steam|howto:dotabuff|unlink|top_heroes|stats:all|stats:ranked)$",
    ))
```

- [ ] **Step 3: Commit**

```bash
git add dota_bot/bot.py
git commit -m "feat: add full profile inline keyboard with stats and hero info"
```

---

### Task 9: Обработка ввода Steam ID текстом

**Files:**
- Modify: `dota_bot/bot.py`

- [ ] **Step 1: Добавить хендлер ввода Steam ID**

Добавить в `dota_bot/bot.py` после `callback_profile`:

```python
async def handle_steam_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_steam_id"):
        return
    context.user_data["awaiting_steam_id"] = False
    user_id = update.effective_user.id
    account_id = _parse_steam_id(update.message.text.strip())
    if account_id is None:
        await update.message.reply_text(
            "❌ Неверный Steam ID. Отправьте число из URL профиля Dotabuff.\n"
            "Пример: 123456789",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❓ Как найти ID?", callback_data="profile:howto")]
            ]),
        )
        context.user_data["awaiting_steam_id"] = True
        return
    _profiles.set(user_id, account_id)
    await update.message.reply_text(
        f"✅ Профиль привязан! Steam ID: {account_id}",
        reply_markup=profile_keyboard_linked(),
    )
```

- [ ] **Step 2: Зарегистрировать хендлер в main()**

В функции `main()` добавить ПЕРЕД регистрацией `callback_pick` (чтобы приоритет был выше):

```python
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_steam_id_input,
    ), group=0)
```

Также убедиться что существующий `handle_menu_button` зарегистрирован в group=1:

```python
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^(🎯 Пик|📈 Мета|🦸 Герой|👤 Профиль)$"),
        handle_menu_button,
    ), group=1)
```

- [ ] **Step 3: Запустить все тесты**

```bash
pytest -v
```

Ожидаем: все PASS

- [ ] **Step 4: Commit**

```bash
git add dota_bot/bot.py
git commit -m "feat: add Steam ID text input handler with validation"
```

---

### Task 10: Push и деплой

- [ ] **Step 1: Запустить все тесты финально**

```bash
pytest -v
```

Ожидаем: все PASS, 0 failures

- [ ] **Step 2: Push на GitHub**

```bash
git push origin feature/dota-bot-v1
```

- [ ] **Step 3: Смержить в main и задеплоить**

```bash
git checkout main
git merge feature/dota-bot-v1
git push origin main
```

Railway автоматически подхватит изменения и передеплоит бота.

- [ ] **Step 4: Проверить в Telegram**

- Нажать "📈 Мета" → появляется выбор позиции → выбрать Carry → получить топ
- Нажать "🦸 Герой" → появляется выбор букв → выбрать группу → выбрать героя → статистика
- Нажать "👤 Профиль" без привязки → кнопка привязать → кнопка "как найти ID"
- Привязать Steam ID → появляется клавиатура с лучшими героями и статистикой
