import logging
import re

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from dota_bot.cache import Cache
from dota_bot.config import BOT_TOKEN, CACHE_FILE, CACHE_TTL_SECONDS, OPENDOTA_API_KEY
from dota_bot.formatter import format_meta, format_picks
from dota_bot.models import HeroInfo, HeroMatchup, HeroMeta, PlayerHeroStats
from dota_bot.parsers.hero_names import HeroNameResolver
from dota_bot.parsers.opendota_api import OpenDotaClient
from dota_bot.profile import ProfileStore
from dota_bot.scorer import score_picks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

WAITING_ENEMIES, WAITING_ALLIES = range(2)

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


# ── /pick conversation ────────────────────────────────────────────────────────

async def pick_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Введите героев врага через запятую:\n\n"
        "Пример: Axe, Invoker, Crystal Maiden, PA, Lion"
    )
    return WAITING_ENEMIES


async def pick_got_enemies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        enemies = _resolver.parse_input(update.message.text)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}\n\nПопробуйте ещё раз:")
        return WAITING_ENEMIES
    context.user_data["enemies"] = [
        {"id": h.id, "slug": h.slug, "localized_name": h.localized_name} for h in enemies
    ]
    await update.message.reply_text(
        "Введите союзных героев через запятую (или /skip чтобы пропустить):\n\n"
        "Пример: Shadow Fiend, Rubick"
    )
    return WAITING_ALLIES


async def pick_got_allies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        _resolver.parse_input(update.message.text)  # validate only; allies unused in v1.0 scoring
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}\n\nПопробуйте ещё раз или /skip:")
        return WAITING_ALLIES
    return await _do_pick(update, context)


async def pick_skip_allies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _do_pick(update, context)


async def _do_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("⏳ Анализирую данные...")
    enemies = [HeroInfo(**h) for h in context.user_data.get("enemies", [])]
    account_id = _profiles.get(update.effective_user.id)
    try:
        id_to_slug = {h.id: h.slug for h in _all_heroes}
        hero_stats = await _fetch_hero_stats()
        enemy_matchups = await _fetch_enemy_matchups(enemies, id_to_slug)
        player_stats: dict[int, PlayerHeroStats] | None = None
        if account_id:
            plist = await _client.get_player_heroes(account_id, id_to_slug)
            player_stats = {p.hero_id: p for p in plist}
        scores = score_picks(enemies, _all_heroes, hero_stats, enemy_matchups, player_stats)
        await update.message.reply_text(format_picks(scores, with_profile=bool(account_id)))
    except Exception:
        logger.exception("Error during /pick")
        await update.message.reply_text("❌ Ошибка при получении данных. Попробуйте позже.")
    return ConversationHandler.END


async def pick_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END


# ── simple commands ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я помогу подобрать оптимальный пик в Dota 2.\n\n"
        "📋 Команды:\n"
        "/pick — подобрать героя по врагам\n"
        "/meta — топ героев текущей меты\n"
        "/hero <имя> — статистика героя\n"
        "/profile — привязать Dotabuff профиль\n"
        "/help — помощь"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 Помощь:\n\n"
        "/pick — запустить подбор пика\n"
        "   Введи героев врага через запятую\n"
        "   Поддерживаются аббревиатуры: am, cm, sf, pa, qop...\n\n"
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
    app.run_polling()


if __name__ == "__main__":
    main()
