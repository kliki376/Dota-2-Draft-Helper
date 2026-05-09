import pytest
from dota_bot.models import HeroScore, HeroMatchup, HeroInfo, HeroMeta
from dota_bot.formatter import format_picks, format_meta

SAMPLE_SCORES = [
    HeroScore(
        hero_slug="silencer",
        localized_name="Silencer",
        score=87.0,
        counter_score=90.0,
        meta_score=75.0,
        pro_score=65.0,
        player_games=0,
        player_win_rate=0.0,
        matchup_details=[
            HeroMatchup(hero_slug="antimage", win_rate=0.62, advantage=0.12),
            HeroMatchup(hero_slug="axe", win_rate=0.60, advantage=0.10),
        ],
    ),
    HeroScore(
        hero_slug="lion",
        localized_name="Lion",
        score=72.0,
        counter_score=65.0,
        meta_score=55.0,
        pro_score=50.0,
        player_games=0,
        player_win_rate=0.0,
        matchup_details=[],
    ),
]


def test_format_picks_contains_hero_names():
    msg = format_picks(SAMPLE_SCORES)
    assert "Silencer" in msg
    assert "Lion" in msg


def test_format_picks_shows_scores():
    msg = format_picks(SAMPLE_SCORES)
    assert "87" in msg


def test_format_picks_shows_counter_info():
    msg = format_picks(SAMPLE_SCORES)
    assert "Anti-Mage" in msg or "antimage" in msg.lower() or "Anti" in msg


def test_format_picks_empty_returns_message():
    msg = format_picks([])
    assert len(msg) > 0


def test_format_picks_with_profile_shows_player_stats():
    scores = [
        HeroScore(
            hero_slug="silencer", localized_name="Silencer",
            score=87.0, counter_score=90.0, meta_score=75.0, pro_score=65.0,
            player_games=127, player_win_rate=0.576,
            matchup_details=[],
        )
    ]
    msg = format_picks(scores, with_profile=True)
    assert "127" in msg
    assert "58%" in msg or "57%" in msg


def test_format_picks_with_profile_low_games_shows_warning():
    scores = [
        HeroScore(
            hero_slug="silencer", localized_name="Silencer",
            score=87.0, counter_score=90.0, meta_score=75.0, pro_score=65.0,
            player_games=3, player_win_rate=0.333,
            matchup_details=[],
        )
    ]
    msg = format_picks(scores, with_profile=True)
    assert "мало" in msg or "⚠️" in msg


def test_format_meta_contains_heroes():
    hero_metas = [
        (HeroInfo(id=75, slug="silencer", localized_name="Silencer"),
         HeroMeta(hero_id=75, hero_slug="silencer", win_rate=0.545, pick_rate=0.6, pro_pick=80, pro_win=44)),
        (HeroInfo(id=26, slug="lion", localized_name="Lion"),
         HeroMeta(hero_id=26, hero_slug="lion", win_rate=0.525, pick_rate=0.7, pro_pick=50, pro_win=26)),
    ]
    msg = format_meta(hero_metas)
    assert "Silencer" in msg
    assert "54" in msg or "55" in msg  # 54.5% displayed
