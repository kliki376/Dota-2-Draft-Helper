from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from dota_bot.models import HeroInfo


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎯 Пик"), KeyboardButton("📈 Мета")],
            [KeyboardButton("🦸 Герой"), KeyboardButton("👤 Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

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


POSITIONS = [
    ("1️⃣ Carry", "meta:pos:1"),
    ("2️⃣ Mid", "meta:pos:2"),
    ("3️⃣ Offlane", "meta:pos:3"),
    ("4️⃣ Soft Support", "meta:pos:4"),
    ("5️⃣ Hard Support", "meta:pos:5"),
]


def meta_position_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(POSITIONS[0][0], callback_data=POSITIONS[0][1]),
         InlineKeyboardButton(POSITIONS[1][0], callback_data=POSITIONS[1][1]),
         InlineKeyboardButton(POSITIONS[2][0], callback_data=POSITIONS[2][1])],
        [InlineKeyboardButton(POSITIONS[3][0], callback_data=POSITIONS[3][1]),
         InlineKeyboardButton(POSITIONS[4][0], callback_data=POSITIONS[4][1])],
        [InlineKeyboardButton("✖ Отмена", callback_data="meta:cancel")],
    ])


def profile_keyboard_unlinked() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Привязать Steam ID", callback_data="profile:link")],
        [InlineKeyboardButton("✖ Закрыть", callback_data="profile:close")],
    ])


def profile_keyboard_linked() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏅 Лучшие герои", callback_data="profile:top_heroes")],
        [InlineKeyboardButton("🎮 Все игры", callback_data="profile:stats:all"),
         InlineKeyboardButton("🏆 Рейтинговые", callback_data="profile:stats:ranked")],
        [InlineKeyboardButton("❌ Отвязать", callback_data="profile:unlink"),
         InlineKeyboardButton("← Назад", callback_data="profile:back")],
    ])


def howto_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Через Steam", callback_data="profile:howto:steam"),
         InlineKeyboardButton("⚔️ Через Dotabuff", callback_data="profile:howto:dotabuff")],
    ])


def hero_info_group_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(label, callback_data=f"hero_info:group:{label}")
            for label, _ in LETTER_GROUPS[:4]
        ],
        [
            InlineKeyboardButton(label, callback_data=f"hero_info:group:{label}")
            for label, _ in LETTER_GROUPS[4:]
        ],
        [InlineKeyboardButton("✖ Отмена", callback_data="hero_info:cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def hero_info_hero_keyboard(heroes: list[HeroInfo]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(h.localized_name, callback_data=f"hero_info:hero:{h.slug}")
        for h in heroes
    ]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton("← Назад", callback_data="hero_info:back")])
    return InlineKeyboardMarkup(rows)
