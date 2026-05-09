import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from dota_bot.cache import Cache
from dota_bot.config import BOT_TOKEN, CACHE_FILE, CACHE_TTL_SECONDS, OPENDOTA_API_KEY
from dota_bot.formatter import format_meta, format_picks
from dota_bot.keyboards import group_keyboard, hero_keyboard, heroes_for_group, main_keyboard
from dota_bot.models import HeroInfo, HeroMatchup, HeroMeta, PlayerHeroStats
from dota_bot.parsers.hero_names import HeroNameResolver
from dota_bot.parsers.opendota_api import OpenDotaClient
from dota_bot.profile import ProfileStore
from dota_bot.scorer import score_picks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_client: OpenDotaClient | None = None
_cache: Cache | None = None
_resolver: HeroNameResolver | None = None
_profiles: ProfileStore | None = None
_all_heroes: list[HeroInfo] = []


# ── data helpers ─────────────────────────────────────────────────────────────

async def _fetch_heroes() -> list[HeroInfo]:
    cached = _cache.get("heroes")
    if cached:
        return [HeroInfo(**h) for h in cached]
    heroes = await _client.get_heroes()
    _cache.set("heroes", [{"id": h.id, "slug": h.slug, "localized_name": h.localized_name} for h in heroes])
    return heroes


async def _fetch_hero_stats() -> dict[int, HeroMeta]:
    cached = _cache.get("hero_stats")
    if cached:
        return {int(k): HeroMeta(**v) for k, v in cached.items()}
    stats = await _client.get_hero_stats()
    _cache.set("hero_stats", {
        str(k): {
            "hero_id": v.hero_id, "hero_slug": v.hero_slug,
            "win_rate": v.win_rate, "pick_rate": v.pick_rate,
            "pro_pick": v.pro_pick, "pro_win": v.pro_win,
        }
        for k, v in stats.items()
    })
    return stats


async def _fetch_enemy_matchups(
    enemies: list[HeroInfo],
    id_to_slug: dict[int, str],
) -> dict[str, list[HeroMatchup]]:
    result: dict[str, list[HeroMatchup]] = {}
    for enemy in enemies:
        cache_key = f"matchups_{enemy.id}"
        cached = _cache.get(cache_key)
        if cached:
            matchups = [HeroMatchup(**m) for m in cached]
        else:
            matchups = await _client.get_hero_matchups(enemy.id, id_to_slug)
            _cache.set(cache_key, [
                {"hero_slug": m.hero_slug, "advantage": m.advantage, "win_rate": m.win_rate}
                for m in matchups
            ])
        result[enemy.slug] = matchups
    return result


def _parse_steam_id(text: str) -> int | None:
    STEAMID64_BASE = 76561197960265728
    if text.isdigit():
        n = int(text)
        return n - STEAMID64_BASE if n > STEAMID64_BASE else n
    match = re.search(r"/players/(\d+)", text)
    return int(match.group(1)) if match else None


def _pick_header(phase: int, count: int, picked_names: list[str] | None = None) -> str:
    label = "Фаза 1" if phase == 1 else "Фаза 2"
    header = f"⚔️ {label} — Враг пикает 2 героев ({count}/2)"
    if picked_names:
        header += "\n" + "\n".join(f"  • {name}" for name in picked_names)
    return header


# ── /pick inline keyboard ─────────────────────────────────────────────────────

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
        enemy_names = [e.localized_name for e in enemies]
        text = format_picks(scores, with_profile=bool(account_id), enemy_names=enemy_names)
        text += "\n\nГотов к фазе 2? Выбери следующих двух врагов."
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
        enemy_names = [e.localized_name for e in all_enemies]
        text = "🏆 Ласт пик\n\n" + format_picks(scores, with_profile=bool(account_id), enemy_names=enemy_names)
        await query.edit_message_text(text)
        context.user_data.clear()
    except Exception:
        logger.exception("Error in phase 2 results")
        await query.edit_message_text("❌ Ошибка при получении данных. Попробуйте позже.")


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
            return  # duplicate — ignore

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


# ── simple commands ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я помогу подобрать оптимальный пик в Dota 2.\n\n"
        "Используй кнопки внизу или команды:\n"
        "/pick — подобрать пик\n"
        "/meta — топ меты\n"
        "/hero <имя> — статистика героя\n"
        "/profile — профиль\n"
        "/help — помощь",
        reply_markup=main_keyboard(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 Помощь:\n\n"
        "/pick — запустить подбор пика\n"
        "   Тапай группу букв → выбирай героя\n\n"
        "/meta — топ-10 героев по winrate в текущем патче\n\n"
        "/hero Crystal Maiden — статистика конкретного героя\n\n"
        "/profile 123456789 — привязать Steam ID (32-bit или 64-bit)\n"
        "/profile — показать привязанный профиль\n"
        "/profile remove — отвязать профиль\n\n"
        "/refresh — принудительно обновить кэш данных"
    )


async def cmd_meta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Загружаю данные меты...")
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
        await update.message.reply_text(format_meta(sorted_heroes))
    except Exception:
        logger.exception("Error during /meta")
        await update.message.reply_text("❌ Ошибка при загрузке данных.")


async def cmd_hero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Укажите имя героя: /hero Crystal Maiden")
        return
    name = " ".join(context.args)
    try:
        hero = _resolver.resolve(name)
    except ValueError:
        await update.message.reply_text(f"❌ Герой не найден: {name}")
        return
    try:
        hero_stats = await _fetch_hero_stats()
        meta = hero_stats.get(hero.id)
        if not meta:
            await update.message.reply_text("Нет данных по этому герою.")
            return
        pro_wr = (
            f"{meta.pro_win / meta.pro_pick * 100:.0f}%"
            if meta.pro_pick >= 20
            else "мало данных"
        )
        await update.message.reply_text(
            f"🦸 {hero.localized_name}\n\n"
            f"📊 Winrate: {meta.win_rate * 100:.1f}%\n"
            f"🏆 Про WR: {pro_wr} ({meta.pro_pick} пиков)\n"
            f"📈 Популярность: {meta.pick_rate * 100:.0f}%"
        )
    except Exception:
        logger.exception("Error during /hero")
        await update.message.reply_text("❌ Ошибка при загрузке данных.")


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args or []
    if not args:
        account_id = _profiles.get(user_id)
        if account_id:
            await update.message.reply_text(
                f"👤 Профиль привязан: Steam ID {account_id}\n"
                f"Данные учитываются при /pick\n\n"
                f"/profile remove — отвязать"
            )
        else:
            await update.message.reply_text(
                "👤 Профиль не привязан.\n\n"
                "Привяжите: /profile <Steam ID>\n"
                "Пример: /profile 123456789"
            )
        return
    if args[0].lower() == "remove":
        _profiles.remove(user_id)
        await update.message.reply_text("✅ Профиль отвязан.")
        return
    account_id = _parse_steam_id(args[0])
    if account_id is None:
        await update.message.reply_text(
            "❌ Неверный Steam ID.\n"
            "Укажите числовой ID из URL профиля Dotabuff.\n"
            "Пример: /profile 123456789"
        )
        return
    _profiles.set(user_id, account_id)
    await update.message.reply_text(f"✅ Профиль привязан: Steam ID {account_id}")


async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _cache.clear()
    await update.message.reply_text("✅ Кэш очищен. Следующий запрос загрузит свежие данные.")


# ── reply keyboard button handler ────────────────────────────────────────────

async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text == "🎯 Пик":
        await cmd_pick(update, context)
    elif text == "📈 Мета":
        await cmd_meta(update, context)
    elif text == "🦸 Герой":
        await update.message.reply_text("Укажите имя героя: /hero Crystal Maiden")
    elif text == "👤 Профиль":
        await cmd_profile(update, context)


# ── application lifecycle ─────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    global _client, _cache, _resolver, _profiles, _all_heroes
    _client = OpenDotaClient(api_key=OPENDOTA_API_KEY)
    _cache = Cache(CACHE_FILE, CACHE_TTL_SECONDS)
    _profiles = ProfileStore("dota_bot/players.json")
    logger.info("Loading hero list...")
    _all_heroes = await _fetch_heroes()
    _resolver = HeroNameResolver(_all_heroes)
    logger.info(f"Ready — {len(_all_heroes)} heroes loaded")


async def post_shutdown(application: Application) -> None:
    if _client:
        await _client.close()


def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("pick", cmd_pick))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^(🎯 Пик|📈 Мета|🦸 Герой|👤 Профиль)$"),
        handle_menu_button,
    ))
    app.add_handler(CallbackQueryHandler(
        callback_pick,
        pattern=r"^(group:[A-Z-]+|hero:[a-z_]+|back|phase2|cancel)$",
    ))
    app.add_handler(CommandHandler("meta", cmd_meta))
    app.add_handler(CommandHandler("hero", cmd_hero))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.run_polling()


if __name__ == "__main__":
    main()
