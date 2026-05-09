from dota_bot.models import HeroScore, HeroInfo, HeroMeta, HeroMetaWithRole, PlayerStats, PlayerHeroStats


def _slug_to_display(slug: str) -> str:
    return slug.replace("_", " ").title()


def format_picks(
    scores: list[HeroScore],
    with_profile: bool = False,
    enemy_names: list[str] | None = None,
) -> str:
    if not scores:
        return "Не удалось найти подходящих героев для текущего драфта."

    parts = []

    if enemy_names:
        parts.append(f"⚔️ Враги: {', '.join(enemy_names)}\n")

    title = "🎯 Контрпики" + (" (с учётом вашей статистики)" if with_profile else "") + ":"
    parts.append(title)

    for i, s in enumerate(scores, 1):
        line = f"\n{i}. {s.localized_name} — {s.score:.0f}/100"
        parts.append(line)

        top_countered = [m for m in s.matchup_details if m.advantage > 0]
        if top_countered:
            counters = ", ".join(
                f"{_slug_to_display(m.hero_slug)} +{m.advantage * 100:.0f}%"
                for m in top_countered[:2]
            )
            parts.append(f"   ⚔️ {counters}")

        parts.append(f"   📊 WR {s.meta_score / 100 * 14 + 43:.1f}% | Про: {s.pro_score:.0f}/100")

        if with_profile:
            if s.player_games > 0:
                wr_pct = s.player_win_rate * 100
                warning = " ⚠️ мало опыта" if s.player_games < 10 else ""
                parts.append(f"   👤 {wr_pct:.0f}% WR | {s.player_games} игр{warning}")
            else:
                parts.append("   👤 Не играли 🆕")

    return "\n".join(parts)


def format_meta(hero_metas: list[tuple[HeroInfo, HeroMeta]]) -> str:
    if not hero_metas:
        return "Нет данных о мете."
    lines = ["📈 Топ героев текущей меты:\n"]
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
