from dota_bot.models import HeroScore, HeroInfo, HeroMeta


def _slug_to_display(slug: str) -> str:
    return slug.replace("_", " ").title()


def format_picks(scores: list[HeroScore], with_profile: bool = False) -> str:
    if not scores:
        return "Не удалось найти подходящих героев для текущего драфта."

    title = "🎯 Идеальный пик"
    if with_profile:
        title += " (с учётом вашей статистики)"
    parts = [title + ":\n"]

    for i, s in enumerate(scores, 1):
        parts.append("━━━━━━━━━━━━━━━━━━━━")
        parts.append(f"{i}. {s.localized_name}  |  Score: {s.score:.0f}/100")
        parts.append("━━━━━━━━━━━━━━━━━━━━")

        top_countered = [m for m in s.matchup_details if m.advantage > 0]
        if top_countered:
            counters = "  ".join(
                f"{_slug_to_display(m.hero_slug)} (+{m.advantage * 100:.0f}%)"
                for m in top_countered[:2]
            )
            parts.append(f"⚔️  Контрпики: {counters}")

        parts.append(f"📊 Мета: {s.meta_score:.0f}/100 | Про: {s.pro_score:.0f}/100")

        if with_profile:
            if s.player_games > 0:
                wr_pct = s.player_win_rate * 100
                warning = " ⚠️ мало опыта" if s.player_games < 10 else ""
                parts.append(f"👤 Ваша статистика: {wr_pct:.0f}% WR | {s.player_games} игр{warning}")
            else:
                parts.append("👤 Вы не играли этим героем 🆕")

        parts.append("")

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
