import pytest
from dota_bot.models import HeroInfo
from dota_bot.parsers.hero_names import HeroNameResolver

SAMPLE_HEROES = [
    HeroInfo(id=1, slug="antimage", localized_name="Anti-Mage"),
    HeroInfo(id=5, slug="crystal_maiden", localized_name="Crystal Maiden"),
    HeroInfo(id=11, slug="nevermore", localized_name="Shadow Fiend"),
    HeroInfo(id=22, slug="zuus", localized_name="Zeus"),
    HeroInfo(id=75, slug="silencer", localized_name="Silencer"),
]


@pytest.fixture
def resolver():
    return HeroNameResolver(SAMPLE_HEROES)


def test_resolve_exact_localized_name(resolver):
    assert resolver.resolve("Anti-Mage").id == 1


def test_resolve_case_insensitive(resolver):
    assert resolver.resolve("anti-mage").id == 1


def test_resolve_slug(resolver):
    assert resolver.resolve("crystal_maiden").id == 5


def test_resolve_alias_am(resolver):
    assert resolver.resolve("am").id == 1


def test_resolve_alias_sf(resolver):
    assert resolver.resolve("sf").id == 11


def test_resolve_alias_cm(resolver):
    assert resolver.resolve("cm").id == 5


def test_resolve_alias_zeus(resolver):
    assert resolver.resolve("zeus").id == 22


def test_resolve_partial_match(resolver):
    assert resolver.resolve("silencer").id == 75


def test_resolve_unknown_raises(resolver):
    with pytest.raises(ValueError, match="Hero not found"):
        resolver.resolve("notahero123")


def test_parse_input_comma_separated(resolver):
    heroes = resolver.parse_input("Anti-Mage, cm, sf")
    assert [h.id for h in heroes] == [1, 5, 11]


def test_parse_input_trims_whitespace(resolver):
    heroes = resolver.parse_input("  anti-mage  ,  crystal maiden  ")
    assert [h.id for h in heroes] == [1, 5]
