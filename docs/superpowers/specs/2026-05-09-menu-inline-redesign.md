# Menu Inline Redesign — Design Spec
Date: 2026-05-09

## Overview

Переработка кнопок Мета, Герой и Профиль: все три открывают inline-клавиатуру вместо текстового ответа.

---

## 1. Мета

**Триггер:** кнопка "📈 Мета" или `/meta`

**Шаг 1 — выбор позиции:**
```
[1️⃣ Carry] [2️⃣ Mid] [3️⃣ Offlane]
[4️⃣ Soft Support] [5️⃣ Hard Support]
[✖ Отмена]
```
Callback data: `meta:pos:1`, `meta:pos:2`, ..., `meta:pos:5`

**Шаг 2 — результат:**
Топ-10 героев меты для выбранной позиции. Фильтрация по полю `lane_role` из OpenDota `/heroStats`. Формат такой же как сейчас (`format_meta`), но с заголовком позиции.

**Данные:** OpenDota `/heroStats` уже содержит `lane_role` (1=Carry, 2=Mid, 3=Offlane, 4=Soft Support, 5=Hard Support). Фильтрация на стороне бота без дополнительных запросов.

---

## 2. Герой

**Триггер:** кнопка "🦸 Герой"

**Шаг 1 — группы букв:** тот же `group_keyboard()` что в Пике.
Callback data: `hero_info:group:A-C`, и т.д.

**Шаг 2 — список героев в группе:** тот же `hero_keyboard()`.
Callback data: `hero_info:hero:slug`

**Шаг 3 — статистика героя:**
```
🦸 Crystal Maiden

📊 Winrate: 52.3%
🏆 Про WR: 55% (120 пиков)
📈 Популярность: 18%
```
Кнопка "← Назад" возвращает к группам букв.

**Изоляция от Пика:** используются отдельные prefix'ы (`hero_info:*`) чтобы не пересекаться с callback'ами пика (`group:*`, `hero:*`).

---

## 3. Профиль

**Триггер:** кнопка "👤 Профиль"

### Состояние А — профиль не привязан:
```
[🔗 Привязать Steam ID]
[✖ Закрыть]
```
Callback data: `profile:link`, `profile:close`

После `profile:link` — бот отвечает текстом:
```
Отправьте ваш Steam ID.

Найти его можно на Dotabuff — это число в URL вашего профиля:
dotabuff.com/players/123456789
                     ↑ вот это число
```
Ссылка на Dotabuff прикладывается как кликабельная. Ждёт следующего текстового сообщения от пользователя через флаг `user_data["awaiting_steam_id"] = True`.

### Состояние Б — профиль привязан:
```
[🏅 Лучшие герои]
[🎮 Все игры] [🏆 Рейтинговые]
[❌ Отвязать] [← Назад]
```
Callback data: `profile:top_heroes`, `profile:stats:all`, `profile:stats:ranked`, `profile:unlink`, `profile:back`

**🏅 Лучшие герои** — топ-5 героев по играм из `/players/{id}/heroes`. Показывает: герой, игры, WR%.

**🎮 Все игры** — `/players/{id}` → поля `win`, `lose`. Показывает: игры всего, WR%, KDA (если доступно). Режим: все кроме lobby/practice (стандартный ответ OpenDota без фильтра).

**🏆 Рейтинговые** — то же что выше но с параметром `?lobby_type=7` (Ranked Matchmaking).

**❌ Отвязать** — удаляет профиль, показывает состояние А.

**← Назад** — закрывает inline-клавиатуру.

---

## Архитектура

### Новые callback-паттерны:
- `meta:pos:[1-5]`, `meta:cancel`
- `hero_info:group:[A-Z-]+`, `hero_info:hero:[a-z_]+`, `hero_info:back`, `hero_info:cancel`
- `profile:link`, `profile:close`, `profile:back`, `profile:top_heroes`, `profile:stats:all`, `profile:stats:ranked`, `profile:unlink`

### Изменения файлов:
- `keyboards.py` — добавить `meta_position_keyboard()`, `profile_keyboard_unlinked()`, `profile_keyboard_linked()`
- `formatter.py` — добавить `format_meta_position()`, `format_player_stats()`, `format_top_heroes()`
- `bot.py` — добавить `callback_meta()`, `callback_hero_info()`, `callback_profile()`, обновить `handle_menu_button()` и регистрацию хендлеров
- `parsers/opendota_api.py` — добавить `get_player_stats(account_id)` и `get_player_stats_ranked(account_id)`

### Ввод Steam ID:
Используем `user_data["awaiting_steam_id"] = True` + MessageHandler с фильтром. Без ConversationHandler — проще и не ломает существующие хендлеры.

---

## Что не меняется
- Reply-клавиатура внизу (4 кнопки) — остаётся как есть
- Логика `/pick` — без изменений
- `/refresh`, `/help`, `/start` — без изменений
