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
