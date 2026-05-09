import io
from unittest.mock import patch

from PIL import Image

from dota_bot.image_gen import build_meta_image
from dota_bot.models import HeroInfo, HeroMeta


def make_hero(slug: str, name: str) -> tuple[HeroInfo, HeroMeta]:
    info = HeroInfo(id=1, slug=slug, localized_name=name)
    meta = HeroMeta(
        hero_id=1, hero_slug=slug,
        win_rate=0.54, pick_rate=0.8,
        pro_pick=50, pro_win=28,
    )
    return info, meta


def test_build_meta_image_returns_bytes():
    heroes = [make_hero("antimage", "Anti-Mage") for _ in range(3)]
    with patch("dota_bot.image_gen._load_icon", return_value=None):
        result = build_meta_image(heroes, title="📈 Топ 10")
    assert isinstance(result, io.BytesIO)
    result.seek(0)
    img = Image.open(result)
    assert img.format == "PNG"
    assert img.width == 420


def test_build_meta_image_height_scales_with_heroes():
    heroes_3 = [make_hero("antimage", "Anti-Mage") for _ in range(3)]
    heroes_10 = [make_hero("antimage", "Anti-Mage") for _ in range(10)]
    with patch("dota_bot.image_gen._load_icon", return_value=None):
        img3 = Image.open(build_meta_image(heroes_3, title="Test"))
        img10 = Image.open(build_meta_image(heroes_10, title="Test"))
    assert img10.height > img3.height
