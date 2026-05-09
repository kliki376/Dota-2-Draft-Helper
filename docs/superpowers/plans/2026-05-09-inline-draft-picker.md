# Inline Draft Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace text-based /pick flow with a 2-phase inline keyboard hero picker that guides the user through enemy picks and returns recommendations after each phase.

**Architecture:** New `keyboards.py` module builds InlineKeyboardMarkup objects. `bot.py` replaces the ConversationHandler-based /pick with a `cmd_pick` CommandHandler and a single `callback_pick` CallbackQueryHandler. State (phase, picked enemies) lives in `context.user_data`. Each button tap edits the same message — no spam.

**Tech Stack:** python-telegram-bot 20.x, InlineKeyboardMarkup, CallbackQueryHandler

---

## File Map

| File | Change | Responsibility |
|------|--------|----------------|
| `dota_bot/keyboards.py` | Create | Build group/hero InlineKeyboardMarkup, hero-to-group mapping |
| `tests/test_keyboards.py` | Create | Unit tests for keyboard builders and group logic |
| `dota_bot/bot.py` | Modify | Remove ConversationHandler, add cmd_pick + callback_pick handlers |

---

### Task 1: keyboards.py

**Files:**
- Create: `dota_bot/keyboards.py`
- Test: `tests/test_keyboards.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_keyboards.py`:

```python
import pytest
from dota_bot.models import HeroInfo
from dota_bot.keyboards import (
    group_keyboard,
    hero_keyboard,
    hero_group,
    heroes_for_group,
    LETTER_GROUPS,
)


def _make(slug, name):
    return HeroInfo(id=1, slug=slug, localized_name=name)


def test_group_keyboard_has_8_group_buttons():
    kb = group_keyboard()
    all_btns = [btn for row in kb.inline_keyboard for btn in row]
    group_btns = [b for b in all_btns if b.callback_data.startswith("group:")]
    assert len(group_btns) == 8


def test_group_keyboard_has_cancel_button():
    kb = group_keyboard()
    all_btns = [btn for row in kb.inline_keyboard for btn in row]
    assert any(b.callback_data == "cancel" for b in all_btns)


def test_hero_keyboard_has_back_button():
    heroes = [_make("antimage", "Anti-Mage")]
    kb = hero_keyboard(heroes, "A-C")
    last_row = kb.inline_keyboard[-1]
    assert last_row[0].callback_data == "back"


def test_hero_keyboard_hero_callback_uses_slug():
    heroes = [_make("antimage", "Anti-Mage")]
    kb = hero_keyboard(heroes, "A-C")
    all_btns = [btn for row in kb.inline_keyboard for btn in row]
    hero_btns = [b for b in all_btns if b.callback_data.startswith("hero:")]
    assert hero_btns[0].callback_data == "hero:antimage"


def test_hero_group_a_c():
    assert hero_group(_make("antimage", "Anti-Mage")) == "A-C"
    assert hero_group(_make("axe", "Axe")) == "A-C"
    assert hero_group(_make("cm", "Crystal Maiden")) == "A-C"


def test_hero_group_d_f():
    assert hero_group(_make("doom", "Doom")) == "D-F"
    assert hero_group(_make("es", "Earth Spirit")) == "D-F"


def test_hero_group_u_z():
    assert hero_group(_make("zuus", "Zeus")) == "U-Z"
    assert hero_group(_make("windrunner", "Windranger")) == "U-Z"


def test_heroes_for_group_filters_correctly():
    heroes = [
        _make("antimage", "Anti-Mage"),
        _make("axe", "Axe"),
        _make("doom", "Doom"),
    ]
    result = heroes_for_group(heroes, "A-C")
    assert len(result) == 2
    assert all(h.localized_name[0].upper() in "ABC" for h in result)


def test_heroes_for_group_sorted_alphabetically():
    heroes = [
        _make("axe", "Axe"),
        _make("antimage", "Anti-Mage"),
    ]
    result = heroes_for_group(heroes, "A-C")
    assert result[0].localized_name == "Anti-Mage"
    assert result[1].localized_name == "Axe"
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd c:\IT_Projects\Project_bot\.worktrees\feature-dota-bot-v1
python -m pytest tests/test_keyboards.py -v
```

Expected: `ModuleNotFoundError: No module named 'dota_bot.keyboards'`

- [ ] **Step 3: Implement keyboards.py**

Create `dota_bot/keyboards.py`:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dota_bot.models import HeroInfo

LETTER_GROUPS: list[tuple[str, str]] = [
    ("A-C", "ABC"),
    ("D-F", "DEF"),
    ("G-I", "GHI"),
    ("J-L", "JKL"),
    ("M-O", "MNO"),
    ("P-R", "PQR"),
    ("S-T", "ST"),
    ("U-Z", "UVWXYZ"),
]


def hero_group(hero: HeroInfo) -> str:
    first = hero.localized_name[0].upper()
    for label, letters in LETTER_GROUPS:
        if first in letters:
            return label
    return "U-Z"


def heroes_for_group(all_heroes: list[HeroInfo], group: str) -> list[HeroInfo]:
    return sorted(
        [h for h in all_heroes if hero_group(h) == group],
        key=lambda h: h.localized_name,
    )


def group_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(label, callback_data=f"group:{label}")
            for label, _ in LETTER_GROUPS[:4]
        ],
        [
            InlineKeyboardButton(label, callback_data=f"group:{label}")
            for label, _ in LETTER_GROUPS[4:]
        ],
        [InlineKeyboardButton("✖ Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def hero_keyboard(heroes: list[HeroInfo], group: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(h.localized_name, callback_data=f"hero:{h.slug}")
        for h in heroes
    ]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton("← Назад", callback_data="back")])
    return InlineKeyboardMarkup(rows)
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest tests/test_keyboards.py -v
```

Expected: 10 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add dota_bot/keyboards.py tests/test_keyboards.py
git commit -m "feat: add inline keyboard builder for hero group picker"
```

---

### Task 2: Update bot.py

**Files:**
- Modify: `dota_bot/bot.py`

- [ ] **Step 1: Replace imports at the top of bot.py**

Replace the full import block (lines 1–20) with:

```python
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from dota_bot.cache import Cache
from dota_bot.config import BOT_TOKEN, CACHE_FILE, CACHE_TTL_SECONDS, OPENDOTA_API_KEY
from dota_bot.formatter import format_meta, format_picks
from dota_bot.keyboards import group_keyboard, hero_keyboard, heroes_for_group
from dota_bot.models import HeroInfo, HeroMatchup, HeroMeta, PlayerHeroStats
from dota_bot.parsers.hero_names import HeroNameResolver
from dota_bot.parsers.opendota_api import OpenDotaClient
from dota_bot.profile import ProfileStore
from dota_bot.scorer import score_picks
```

- [ ] **Step 2: Remove ConversationHandler constants and old /pick handlers**

Delete these lines (they appear right after imports):

```python
WAITING_ENEMIES, WAITING_ALLIES = range(2)
```

Delete these entire functions:
- `pick_start`
- `pick_got_enemies`
- `pick_got_allies`
- `pick_skip_allies`
- `_do_pick`
- `pick_cancel`

- [ ] **Step 3: Add _pick_header helper after the data helpers block**

Add this function after `_parse_steam_id`:

```python
def _pick_header(phase: int, count: int, picked_names: list[str] | None = None) -> str:
    label = "Фаза 1" if phase == 1 else "Фаза 2"
    header = f"⚔️ {label} — Враг пикает 2 героев ({count}/2)"
    if picked_names:
        header += "\n" + "\n".join(f"  • {name}" for name in picked_names)
    return header
```

- [ ] **Step 4: Add cmd_pick handler after _pick_header**

```python
async def cmd_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.update({
        "phase": 1,
        "phase1_enemies": [],
        "current_picks": [],
    })
    await update.message.reply_text(
        _pick_header(1, 0),
        reply_markup=group_keyboard(),
    )
```

- [ ] **Step 5: Add _show_phase1_results and _show_phase2_results helpers**

Add these two functions after `cmd_pick`:

```python
async def _show_phase1_results(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    enemies = [HeroInfo(**p) for p in context.user_data["phase1_enemies"]]
    id_to_slug = {h.id: h.slug for h in _all_heroes}
    try:
        hero_stats = await _fetch_hero_stats()
        enemy_matchups = await _fetch_enemy_matchups(enemies, id_to_slug)
        account_id = _profiles.get(query.from_user.id)
        player_stats = None
        if account_id:
            plist = await _client.get_player_heroes(account_id, id_to_slug)
            player_stats = {p.hero_id: p for p in plist}
        scores = score_picks(enemies, _all_heroes, hero_stats, enemy_matchups, player_stats)
        text = format_picks(scores, with_profile=bool(account_id))
        text += "\n\n━━━━━━━━━━━━━━━━━━━━\nГотов к фазе 2? Выбери следующих двух врагов."
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Фаза 2 →", callback_data="phase2")],
                [InlineKeyboardButton("✖ Завершить", callback_data="cancel")],
            ]),
        )
    except Exception:
        logger.exception("Error in phase 1 results")
        await query.edit_message_text("❌ Ошибка при получении данных. Попробуйте позже.")


async def _show_phase2_results(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    phase1 = [HeroInfo(**p) for p in context.user_data["phase1_enemies"]]
    phase2 = [HeroInfo(**p) for p in context.user_data["current_picks"]]
    all_enemies = phase1 + phase2
    id_to_slug = {h.id: h.slug for h in _all_heroes}
    try:
        hero_stats = await _fetch_hero_stats()
        enemy_matchups = await _fetch_enemy_matchups(all_enemies, id_to_slug)
        account_id = _profiles.get(query.from_user.id)
        player_stats = None
        if account_id:
            plist = await _client.get_player_heroes(account_id, id_to_slug)
            player_stats = {p.hero_id: p for p in plist}
        scores = score_picks(all_enemies, _all_heroes, hero_stats, enemy_matchups, player_stats, top_n=3)
        text = "🏆 Ласт пик — лучший выбор против всех 4 врагов:\n\n"
        text += format_picks(scores, with_profile=bool(account_id))
        await query.edit_message_text(text)
        context.user_data.clear()
    except Exception:
        logger.exception("Error in phase 2 results")
        await query.edit_message_text("❌ Ошибка при получении данных. Попробуйте позже.")
```

- [ ] **Step 6: Add callback_pick handler**

Add after `_show_phase2_results`:

```python
async def callback_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel":
        await query.edit_message_text("❌ Драфт отменён.")
        context.user_data.clear()
        return

    if data == "phase2":
        context.user_data["phase"] = 2
        context.user_data["current_picks"] = []
        await query.edit_message_text(
            _pick_header(2, 0),
            reply_markup=group_keyboard(),
        )
        return

    if data == "back":
        phase = context.user_data.get("phase", 1)
        picks = context.user_data.get("current_picks", [])
        await query.edit_message_text(
            _pick_header(phase, len(picks), [p["localized_name"] for p in picks]),
            reply_markup=group_keyboard(),
        )
        return

    if data.startswith("group:"):
        group = data[6:]
        phase = context.user_data.get("phase", 1)
        picks = context.user_data.get("current_picks", [])
        heroes = heroes_for_group(_all_heroes, group)
        await query.edit_message_text(
            _pick_header(phase, len(picks), [p["localized_name"] for p in picks]),
            reply_markup=hero_keyboard(heroes, group),
        )
        return

    if data.startswith("hero:"):
        slug = data[5:]
        picks = context.user_data.setdefault("current_picks", [])
        phase = context.user_data.get("phase", 1)

        if any(p["slug"] == slug for p in picks):
            return  # duplicate — ignore silently

        hero = next((h for h in _all_heroes if h.slug == slug), None)
        if hero is None:
            return

        picks.append({
            "id": hero.id,
            "slug": hero.slug,
            "localized_name": hero.localized_name,
        })

        if len(picks) < 2:
            await query.edit_message_text(
                _pick_header(phase, len(picks), [p["localized_name"] for p in picks]),
                reply_markup=group_keyboard(),
            )
            return

        if phase == 1:
            context.user_data["phase1_enemies"] = picks[:]
            await _show_phase1_results(query, context)
        else:
            await _show_phase2_results(query, context)
```

- [ ] **Step 7: Update main() to register new handlers**

Find the `main()` function and replace its handler registration block:

Old (remove):
```python
    conv = ConversationHandler(
        entry_points=[CommandHandler("pick", pick_start)],
        states={
            WAITING_ENEMIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, pick_got_enemies)],
            WAITING_ALLIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pick_got_allies),
                CommandHandler("skip", pick_skip_allies),
            ],
        },
        fallbacks=[CommandHandler("cancel", pick_cancel)],
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(conv)
    app.add_handler(CommandHandler("meta", cmd_meta))
    app.add_handler(CommandHandler("hero", cmd_hero))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
```

New (replace with):
```python
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pick", cmd_pick))
    app.add_handler(CallbackQueryHandler(
        callback_pick,
        pattern=r"^(group:[A-Z-]+|hero:[a-z_]+|back|phase2|cancel)$",
    ))
    app.add_handler(CommandHandler("meta", cmd_meta))
    app.add_handler(CommandHandler("hero", cmd_hero))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
```

- [ ] **Step 8: Run full test suite**

```
python -m pytest -v
```

Expected: 54 passed (44 existing + 10 keyboards)

- [ ] **Step 9: Commit**

```bash
git add dota_bot/bot.py
git commit -m "feat: replace text /pick with inline keyboard 2-phase draft picker"
```

---

### Task 3: Manual test

- [ ] **Step 1: Start the bot**

```
cd c:\IT_Projects\Project_bot\.worktrees\feature-dota-bot-v1
python -m dota_bot.bot
```

Expected log: `Ready — 127 heroes loaded`

- [ ] **Step 2: Test full flow in Telegram**

1. Send `/pick` → should see "Фаза 1 — Враг пикает 2 героев (0/2)" with 8 group buttons
2. Tap `A-C` → should see hero buttons (Abaddon, Alchemist, Anti-Mage, ...)
3. Tap `Anti-Mage` → message updates to (1/2), shows "Anti-Mage" in the picked list, group picker returns
4. Tap `D-F` → Doom, Dawnbreaker, etc.
5. Tap `Doom` → (2/2) complete, recommendations appear + "Фаза 2 →" button
6. Tap `Фаза 2 →` → "Фаза 2 — Враг пикает 2 героев (0/2)", group picker
7. Pick 2 more heroes → "🏆 Ласт пик" results appear
8. Test `✖ Отмена` → "❌ Драфт отменён."
9. Test `← Назад` from hero list → returns to group picker
10. Test duplicate: tap same hero twice → no duplicate in picks
