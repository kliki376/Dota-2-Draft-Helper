# Hero Icons in Meta — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Генерировать PNG-картинку с иконками героев для результатов Меты вместо текстового сообщения.

**Architecture:** Новый модуль `image_gen.py` скачивает иконки с Valve CDN, кеширует на диске, генерирует PNG через Pillow. `callback_meta` в `bot.py` отправляет фото вместо текста. Всё остальное не меняется.

**Tech Stack:** Python 3.11, Pillow 10.3.0, httpx (уже есть), python-telegram-bot 20.7

---

## File Map

- **Create:** `dota_bot/image_gen.py` — генерация PNG с иконками
- **Modify:** `requirements.txt` — добавить Pillow
- **Modify:** `.gitignore` — добавить `dota_bot/icons/`
- **Modify:** `dota_bot/bot.py` — `callback_meta` использует фото вместо текста
- **Create:** `tests/test_image_gen.py` — тесты генератора

---

### Task 1: Добавить Pillow и обновить .gitignore

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Добавить Pillow в requirements.txt**

Открыть `requirements.txt` и добавить строку:
```
Pillow==10.3.0
```

- [ ] **Step 2: Добавить icons/ в .gitignore**

Открыть `.gitignore` и добавить строку:
```
dota_bot/icons/
```

- [ ] **Step 3: Установить Pillow**

```bash
pip install Pillow==10.3.0
```

Ожидаем: `Successfully installed Pillow-10.3.0`

- [ ] **Step 4: Проверить импорт**

```bash
python -c "from PIL import Image, ImageDraw, ImageFont; print('OK')"
```

Ожидаем: `OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: add Pillow dependency and ignore icons cache"
```

---

### Task 2: Создать модуль image_gen.py

**Files:**
- Create: `dota_bot/image_gen.py`
- Create: `tests/test_image_gen.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_image_gen.py`:

```python
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from dota_bot.image_gen import build_meta_image
from dota_bot.models import HeroInfo, HeroMeta


def make_hero(slug: str, name: str) -> tuple[HeroInfo, HeroMeta]:
    info = HeroInfo(id=1, slug=slug, localized_name=name)
    meta = HeroMeta(
        hero_id=1, hero_slug=slug,
        win_rate=0.54, pick_rate=0.8,
        pro_pick=50, pro_win=28,
    )
    return info, meta


def test_build_meta_image_returns_bytes():
    heroes = [make_hero("antimage", "Anti-Mage") for _ in range(3)]
    with patch("dota_bot.image_gen._load_icon", return_value=None):
        result = build_meta_image(heroes, title="📈 Топ 10")
    assert isinstance(result, io.BytesIO)
    result.seek(0)
    img = Image.open(result)
    assert img.format == "PNG"
    assert img.width == 420


def test_build_meta_image_height_scales_with_heroes():
    heroes_3 = [make_hero("antimage", "Anti-Mage") for _ in range(3)]
    heroes_10 = [make_hero("antimage", "Anti-Mage") for _ in range(10)]
    with patch("dota_bot.image_gen._load_icon", return_value=None):
        img3 = Image.open(build_meta_image(heroes_3, title="Test"))
        img10 = Image.open(build_meta_image(heroes_10, title="Test"))
    assert img10.height > img3.height
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd "C:\IT_Projects\Project_bot\.worktrees\feature-dota-bot-v1"
python -m pytest tests/test_image_gen.py -v
```

Ожидаем: FAIL — `ModuleNotFoundError: No module named 'dota_bot.image_gen'`

- [ ] **Step 3: Создать dota_bot/image_gen.py**

```python
import io
import os
import httpx
from PIL import Image, ImageDraw, ImageFont

from dota_bot.models import HeroInfo, HeroMeta

ICONS_DIR = os.path.join(os.path.dirname(__file__), "icons")
ICON_URL = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/{slug}_icon.png"

IMG_WIDTH = 420
ROW_HEIGHT = 40
PADDING_TOP = 50
PADDING_BOTTOM = 20
PADDING_LEFT = 10

BG_COLOR = (26, 26, 46)
TEXT_COLOR = (255, 255, 255)
STATS_COLOR = (170, 170, 170)
NUM_COLOR = (245, 197, 24)


def _load_icon(slug: str) -> Image.Image | None:
    os.makedirs(ICONS_DIR, exist_ok=True)
    path = os.path.join(ICONS_DIR, f"{slug}.png")
    if os.path.exists(path):
        try:
            return Image.open(path).convert("RGBA").resize((32, 32))
        except Exception:
            return None
    try:
        resp = httpx.get(ICON_URL.format(slug=slug), timeout=5.0)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
        return Image.open(io.BytesIO(resp.content)).convert("RGBA").resize((32, 32))
    except Exception:
        return None


def _get_font(size: int = 14):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def build_meta_image(
    heroes: list[tuple[HeroInfo, HeroMeta]],
    title: str,
) -> io.BytesIO:
    total_height = PADDING_TOP + len(heroes) * ROW_HEIGHT + PADDING_BOTTOM
    img = Image.new("RGB", (IMG_WIDTH, total_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(16)
    font_name = _get_font(14)
    font_stats = _get_font(13)

    draw.text((PADDING_LEFT, 12), title, font=font_title, fill=TEXT_COLOR)

    for i, (info, meta) in enumerate(heroes):
        y = PADDING_TOP + i * ROW_HEIGHT

        draw.text((PADDING_LEFT, y + 10), f"{i + 1}.", font=font_name, fill=NUM_COLOR)

        icon = _load_icon(info.slug)
        if icon:
            img.paste(icon, (PADDING_LEFT + 24, y + 4), icon)

        pro_wr = (
            f"{meta.pro_win / meta.pro_pick * 100:.0f}%"
            if meta.pro_pick >= 20
            else "—"
        )
        name_x = PADDING_LEFT + 24 + 32 + 8
        draw.text((name_x, y + 4), info.localized_name, font=font_name, fill=TEXT_COLOR)
        stats = f"WR {meta.win_rate * 100:.1f}% | Про: {pro_wr}"
        draw.text((name_x, y + 22), stats, font=font_stats, fill=STATS_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
```

- [ ] **Step 4: Запустить тест — убедиться что проходит**

```bash
python -m pytest tests/test_image_gen.py -v
```

Ожидаем: PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/image_gen.py tests/test_image_gen.py
git commit -m "feat: add image_gen module for hero icon meta images"
```

---

### Task 3: Обновить callback_meta в bot.py

**Files:**
- Modify: `dota_bot/bot.py`

- [ ] **Step 1: Добавить импорт image_gen в bot.py**

В начале `dota_bot/bot.py` добавить импорт:

```python
from dota_bot.image_gen import build_meta_image
```

- [ ] **Step 2: Заменить meta:top10 блок**

Найти в `callback_meta` блок `if data == "meta:top10":` и заменить целиком:

```python
    if data == "meta:top10":
        await query.edit_message_text("⏳ Загружаю данные меты...")
        try:
            hero_stats = await _fetch_hero_stats()
            hero_info_map = {h.id: h for h in _all_heroes}
            sorted_heroes = sorted(
                [
                    (hero_info_map[hid], meta)
                    for hid, meta in hero_stats.items()
                    if hid in hero_info_map and meta.pick_rate > 0.05
                ],
                key=lambda x: x[1].win_rate,
                reverse=True,
            )[:10]
            image = build_meta_image(sorted_heroes, title="📈 Топ 10 общая мета")
            await query.message.reply_photo(photo=image, caption="📈 Топ 10 общая мета")
            await query.message.delete()
        except Exception:
            logger.exception("Error in callback_meta top10")
            await query.edit_message_text("❌ Ошибка при загрузке данных.")
        return
```

- [ ] **Step 3: Заменить meta:pos: блок**

Найти блок `if data.startswith("meta:pos:"):` и заменить целиком:

```python
    if data.startswith("meta:pos:"):
        position = int(data[-1])
        pos_names = {1: "Carry", 2: "Mid", 3: "Offlane", 4: "Soft Support", 5: "Hard Support"}
        pos_name = pos_names.get(position, str(position))
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
            title = f"📈 Топ {len(filtered)} — {pos_name}"
            image = build_meta_image(filtered, title=title)
            await query.message.reply_photo(photo=image, caption=title)
            await query.message.delete()
        except Exception:
            logger.exception("Error in callback_meta")
            await query.edit_message_text("❌ Ошибка при загрузке данных.")
```

- [ ] **Step 4: Запустить все тесты**

```bash
python -m pytest -v
```

Ожидаем: все PASS

- [ ] **Step 5: Commit**

```bash
git add dota_bot/bot.py
git commit -m "feat: send hero icon image in meta results"
```

---

### Task 4: Push и деплой

- [ ] **Step 1: Финальный прогон тестов**

```bash
python -m pytest -v
```

Ожидаем: все PASS, 0 failures

- [ ] **Step 2: Push feature branch**

```bash
git push origin feature/dota-bot-v1
```

- [ ] **Step 3: Merge в main и деплой**

```bash
git checkout main  # или cd C:\IT_Projects\Project_bot
git merge feature/dota-bot-v1 --no-edit
git push origin main
```

Railway автоматически задеплоит. На Railway нужно убедиться что Pillow установится — он есть в `requirements.txt`.

- [ ] **Step 4: Проверить в Telegram**

- Нажать "📈 Мета" → "📊 Топ 10 общая" → должна прийти картинка с иконками
- Нажать "📈 Мета" → "1️⃣ Carry" → картинка с героями керри
