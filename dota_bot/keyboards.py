from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dota_bot.models import HeroInfo

LETTER_GROUPS: list[tuple[str, str]] = [
    ("A-C", "ABC"),
    ("D-F", "DEF"),
    ("G-I", "GHI"),
    ("J-L", "JKL"),
    ("M-O", "MNO"),
    ("P-R", "PQR"),
    ("S-T", "ST"),
    ("U-Z", "UVWXYZ"),
]


def hero_group(hero: HeroInfo) -> str:
    first = hero.localized_name[0].upper()
    for label, letters in LETTER_GROUPS:
        if first in letters:
            return label
    return "U-Z"


def heroes_for_group(all_heroes: list[HeroInfo], group: str) -> list[HeroInfo]:
    return sorted(
        [h for h in all_heroes if hero_group(h) == group],
        key=lambda h: h.localized_name,
    )


def group_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(label, callback_data=f"group:{label}")
            for label, _ in LETTER_GROUPS[:4]
        ],
        [
            InlineKeyboardButton(label, callback_data=f"group:{label}")
            for label, _ in LETTER_GROUPS[4:]
        ],
        [InlineKeyboardButton("✖ Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def hero_keyboard(heroes: list[HeroInfo], group: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(h.localized_name, callback_data=f"hero:{h.slug}")
        for h in heroes
    ]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton("← Назад", callback_data="back")])
    return InlineKeyboardMarkup(rows)
