from dota_bot.models import HeroInfo, HeroMeta, HeroMatchup, PlayerHeroStats, HeroScore

MIN_META_WINRATE = 0.47


def _counter_score(
    candidate_slug: str,
    enemy_matchups: dict[str, list[HeroMatchup]],
) -> tuple[float, list[HeroMatchup]]:
    advantages = []
    details = []
    for enemy_slug, matchups in enemy_matchups.items():
        for m in matchups:
            if m.hero_slug == candidate_slug:
                # m.win_rate = enemy's WR vs candidate → invert
                candidate_wr = 1.0 - m.win_rate
                advantage = candidate_wr - 0.5
                advantages.append(advantage)
                details.append(HeroMatchup(
                    hero_slug=enemy_slug,
                    win_rate=candidate_wr,
                    advantage=advantage,
                ))
                break
    if not advantages:
        return 50.0, []
    avg_adv = sum(advantages) / len(advantages)
    score = (avg_adv / 0.2 + 1.0) * 50.0
    return max(0.0, min(100.0, score)), details


def _meta_score(meta: HeroMeta) -> float:
    # 43% WR → 0, 50% WR → 50, 57% WR → 100
    return max(0.0, min(100.0, (meta.win_rate - 0.43) / 0.14 * 100))


def _pro_score(meta: HeroMeta) -> float:
    if meta.pro_pick < 20:
        return 45.0
    pro_wr = meta.pro_win / meta.pro_pick
    return max(0.0, min(100.0, (pro_wr - 0.3) / 0.4 * 100))


def _player_score(ph: PlayerHeroStats | None) -> float:
    if ph is None or ph.games == 0:
        return 30.0
    return min(100.0, ph.win_rate * 60 + min(ph.games / 100, 1.0) * 40)


def score_picks(
    enemies: list[HeroInfo],
    all_heroes: list[HeroInfo],
    hero_stats: dict[int, HeroMeta],
    enemy_matchups: dict[str, list[HeroMatchup]],
    player_stats: dict[int, PlayerHeroStats] | None = None,
    top_n: int = 5,
) -> list[HeroScore]:
    enemy_ids = {e.id for e in enemies}
    scores = []
    for hero in all_heroes:
        if hero.id in enemy_ids:
            continue
        meta = hero_stats.get(hero.id)
        if meta is None or meta.win_rate < MIN_META_WINRATE:
            continue
        cs, details = _counter_score(hero.slug, enemy_matchups)
        ms = _meta_score(meta)
        ps = _pro_score(meta)
        ph = player_stats.get(hero.id) if player_stats else None
        if player_stats is not None:
            total = cs * 0.35 + ms * 0.20 + ps * 0.15 + _player_score(ph) * 0.30
            player_games = ph.games if ph else 0
            player_wr = ph.win_rate if ph else 0.0
        else:
            total = cs * 0.55 + ms * 0.25 + ps * 0.20
            player_games = 0
            player_wr = 0.0
        scores.append(HeroScore(
            hero_slug=hero.slug,
            localized_name=hero.localized_name,
            score=round(total, 1),
            counter_score=round(cs, 1),
            meta_score=round(ms, 1),
            pro_score=round(ps, 1),
            player_games=player_games,
            player_win_rate=round(player_wr, 3),
            matchup_details=sorted(details, key=lambda m: m.advantage, reverse=True)[:3],
        ))
    return sorted(scores, key=lambda s: s.score, reverse=True)[:top_n]
