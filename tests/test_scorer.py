import pytest
from dota_bot.models import HeroInfo, HeroMeta, HeroMatchup, PlayerHeroStats
from dota_bot.scorer import score_picks, _counter_score, _meta_score, _pro_score

ENEMIES = [
    HeroInfo(id=1, slug="antimage", localized_name="Anti-Mage"),
    HeroInfo(id=2, slug="axe", localized_name="Axe"),
]

ALL_HEROES = [
    HeroInfo(id=1, slug="antimage", localized_name="Anti-Mage"),
    HeroInfo(id=2, slug="axe", localized_name="Axe"),
    HeroInfo(id=75, slug="silencer", localized_name="Silencer"),
    HeroInfo(id=26, slug="lion", localized_name="Lion"),
    HeroInfo(id=35, slug="clinkz", localized_name="Clinkz"),
    HeroInfo(id=99, slug="bristleback", localized_name="Bristleback"),
]

# enemy_matchups: {enemy_slug: [matchups from enemy's perspective]}
# Entry {hero_slug: "silencer", win_rate: 0.38} means enemy has 38% WR vs Silencer
# → Silencer has 62% WR vs this enemy → counters well
ENEMY_MATCHUPS = {
    "antimage": [
        HeroMatchup(hero_slug="silencer", win_rate=0.38, advantage=-0.12),  # AM bad vs Silencer
        HeroMatchup(hero_slug="lion", win_rate=0.48, advantage=-0.02),
        HeroMatchup(hero_slug="clinkz", win_rate=0.52, advantage=0.02),
        HeroMatchup(hero_slug="bristleback", win_rate=0.55, advantage=0.05),
    ],
    "axe": [
        HeroMatchup(hero_slug="silencer", win_rate=0.40, advantage=-0.10),  # Axe bad vs Silencer
        HeroMatchup(hero_slug="lion", win_rate=0.49, advantage=-0.01),
        HeroMatchup(hero_slug="clinkz", win_rate=0.51, advantage=0.01),
        HeroMatchup(hero_slug="bristleback", win_rate=0.45, advantage=-0.05),
    ],
}

HERO_STATS = {
    75: HeroMeta(hero_id=75, hero_slug="silencer", win_rate=0.525, pick_rate=0.6, pro_pick=80, pro_win=44),
    26: HeroMeta(hero_id=26, hero_slug="lion", win_rate=0.51, pick_rate=0.7, pro_pick=50, pro_win=26),
    35: HeroMeta(hero_id=35, hero_slug="clinkz", win_rate=0.465, pick_rate=0.3, pro_pick=10, pro_win=5),
    99: HeroMeta(hero_id=99, hero_slug="bristleback", win_rate=0.51, pick_rate=0.5, pro_pick=30, pro_win=18),
    1: HeroMeta(hero_id=1, hero_slug="antimage", win_rate=0.50, pick_rate=1.0, pro_pick=100, pro_win=50),
    2: HeroMeta(hero_id=2, hero_slug="axe", win_rate=0.52, pick_rate=0.8, pro_pick=60, pro_win=33),
}


def test_counter_score_high_for_strong_counter():
    matchups = {"antimage": [HeroMatchup(hero_slug="silencer", win_rate=0.38, advantage=-0.12)]}
    score, _ = _counter_score("silencer", matchups)
    # candidate WR vs AM = 1 - 0.38 = 0.62 → advantage = 0.12
    # score = (0.12/0.2 + 1) * 50 = (0.6 + 1) * 50 = 80
    assert score == pytest.approx(80.0)


def test_counter_score_neutral_when_no_matchup_data():
    score, _ = _counter_score("unknown_hero", {"antimage": []})
    assert score == pytest.approx(50.0)


def test_meta_score_average_hero():
    meta = HeroMeta(hero_id=1, hero_slug="x", win_rate=0.50, pick_rate=0.5, pro_pick=0, pro_win=0)
    assert _meta_score(meta) == pytest.approx(50.0)


def test_meta_score_strong_hero():
    meta = HeroMeta(hero_id=1, hero_slug="x", win_rate=0.57, pick_rate=0.5, pro_pick=0, pro_win=0)
    assert _meta_score(meta) == pytest.approx(100.0)


def test_pro_score_neutral_when_few_picks():
    meta = HeroMeta(hero_id=1, hero_slug="x", win_rate=0.50, pick_rate=0.5, pro_pick=5, pro_win=3)
    assert _pro_score(meta) == pytest.approx(45.0)


def test_score_picks_excludes_enemies():
    scores = score_picks(ENEMIES, ALL_HEROES, HERO_STATS, ENEMY_MATCHUPS)
    slugs = [s.hero_slug for s in scores]
    assert "antimage" not in slugs
    assert "axe" not in slugs


def test_score_picks_excludes_below_winrate_threshold():
    # clinkz has 46.5% WR < 47% threshold → excluded
    scores = score_picks(ENEMIES, ALL_HEROES, HERO_STATS, ENEMY_MATCHUPS)
    slugs = [s.hero_slug for s in scores]
    assert "clinkz" not in slugs


def test_score_picks_silencer_ranks_first():
    # Silencer has strong counter vs both enemies
    scores = score_picks(ENEMIES, ALL_HEROES, HERO_STATS, ENEMY_MATCHUPS)
    assert scores[0].hero_slug == "silencer"


def test_score_picks_returns_at_most_top_n():
    scores = score_picks(ENEMIES, ALL_HEROES, HERO_STATS, ENEMY_MATCHUPS, top_n=2)
    assert len(scores) <= 2


def test_score_picks_with_player_stats_adjusts_score():
    player_stats = {
        75: PlayerHeroStats(hero_id=75, hero_slug="silencer", games=200, wins=120),
        26: PlayerHeroStats(hero_id=26, hero_slug="lion", games=0, wins=0),
    }
    scores_no_profile = score_picks(ENEMIES, ALL_HEROES, HERO_STATS, ENEMY_MATCHUPS)
    scores_with_profile = score_picks(ENEMIES, ALL_HEROES, HERO_STATS, ENEMY_MATCHUPS, player_stats=player_stats)
    silencer_no = next(s for s in scores_no_profile if s.hero_slug == "silencer")
    silencer_with = next(s for s in scores_with_profile if s.hero_slug == "silencer")
    assert silencer_with.player_games == 200
    assert silencer_with.player_win_rate == pytest.approx(120 / 200)
