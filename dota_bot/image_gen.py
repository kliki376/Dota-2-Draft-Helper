import io
import os

import httpx
from PIL import Image, ImageDraw, ImageFont

from dota_bot.models import HeroInfo, HeroMeta

ICONS_DIR = os.path.join(os.path.dirname(__file__), "icons")
ICON_URL = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/{slug}_icon.png"

IMG_WIDTH = 420
ROW_HEIGHT = 40
PADDING_TOP = 50
PADDING_BOTTOM = 20
PADDING_LEFT = 10

BG_COLOR = (26, 26, 46)
TEXT_COLOR = (255, 255, 255)
STATS_COLOR = (170, 170, 170)
NUM_COLOR = (245, 197, 24)


def _load_icon(slug: str) -> Image.Image | None:
    os.makedirs(ICONS_DIR, exist_ok=True)
    path = os.path.join(ICONS_DIR, f"{slug}.png")
    if os.path.exists(path):
        try:
            return Image.open(path).convert("RGBA").resize((32, 32))
        except Exception:
            return None
    try:
        resp = httpx.get(ICON_URL.format(slug=slug), timeout=5.0)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
        return Image.open(io.BytesIO(resp.content)).convert("RGBA").resize((32, 32))
    except Exception:
        return None


def _get_font(size: int = 14) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def build_meta_image(
    heroes: list[tuple[HeroInfo, HeroMeta]],
    title: str,
) -> io.BytesIO:
    total_height = PADDING_TOP + len(heroes) * ROW_HEIGHT + PADDING_BOTTOM
    img = Image.new("RGB", (IMG_WIDTH, total_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(16)
    font_name = _get_font(14)
    font_stats = _get_font(13)

    draw.text((PADDING_LEFT, 12), title, font=font_title, fill=TEXT_COLOR)

    for i, (info, meta) in enumerate(heroes):
        y = PADDING_TOP + i * ROW_HEIGHT

        draw.text((PADDING_LEFT, y + 10), f"{i + 1}.", font=font_name, fill=NUM_COLOR)

        icon = _load_icon(info.slug)
        if icon:
            img.paste(icon, (PADDING_LEFT + 24, y + 4), icon)

        pro_wr = (
            f"{meta.pro_win / meta.pro_pick * 100:.0f}%"
            if meta.pro_pick >= 20
            else "—"
        )
        name_x = PADDING_LEFT + 24 + 32 + 8
        draw.text((name_x, y + 4), info.localized_name, font=font_name, fill=TEXT_COLOR)
        stats = f"WR {meta.win_rate * 100:.1f}% | Про: {pro_wr}"
        draw.text((name_x, y + 22), stats, font=font_stats, fill=STATS_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
