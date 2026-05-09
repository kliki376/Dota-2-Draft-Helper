HERO_PRIMARY_POSITION: dict[str, int] = {
    # Position 1 — Carry
    "antimage": 1, "juggernaut": 1, "morphling": 1, "phantom_lancer": 1,
    "drow_ranger": 1, "chaos_knight": 1, "faceless_void": 1, "phantom_assassin": 1,
    "spectre": 1, "terrorblade": 1, "luna": 1, "weaver": 1, "gyrocopter": 1,
    "medusa": 1, "naga_siren": 1, "troll_warlord": 1, "slark": 1, "ursa": 1,
    "wraith_king": 1, "lifestealer": 1, "clinkz": 1, "lone_druid": 1,
    "meepo": 1, "arc_warden": 1, "monkey_king": 1, "bloodseeker": 1,
    "razor": 1, "viper": 1, "huskar": 1, "alchemist": 1, "sven": 1,
    "riki": 1, "sniper": 1, "windranger": 1, "muerta": 1,

    # Position 2 — Mid
    "invoker": 2, "shadow_fiend": 2, "storm_spirit": 2, "queen_of_pain": 2,
    "tinker": 2, "puck": 2, "lina": 2, "dragon_knight": 2, "death_prophet": 2,
    "outworld_destroyer": 2, "ember_spirit": 2, "void_spirit": 2,
    "templar_assassin": 2, "zeus": 2, "leshrac": 2, "ancient_apparition": 2,
    "visage": 2, "batrider": 2, "skywrath_mage": 2, "pugna": 2,
    "kunkka": 2, "night_stalker": 2, "arc_warden": 2, "silencer": 2,
    "witch_doctor": 2,

    # Position 3 — Offlane
    "axe": 3, "tidehunter": 3, "beastmaster": 3, "centaur": 3,
    "brewmaster": 3, "dark_seer": 3, "underlord": 3, "timbersaw": 3,
    "bristleback": 3, "magnus": 3, "doom": 3, "phoenix": 3,
    "clockwerk": 3, "spirit_breaker": 3, "lycan": 3, "mars": 3,
    "pangolier": 3, "slardar": 3, "sand_king": 3, "omniknight": 3,
    "enigma": 3, "nature_prophet": 3, "nightstalker": 3,
    "primal_beast": 3, "legion_commander": 3, "pudge": 3,

    # Position 4 — Soft Support
    "earthshaker": 4, "lion": 4, "shadow_shaman": 4, "bounty_hunter": 4,
    "disruptor": 4, "elder_titan": 4, "vengefulspirit": 4, "tusk": 4,
    "nyx_assassin": 4, "snapfire": 4, "marci": 4, "jakiro": 4,
    "bloodseeker": 4, "sand_king": 4, "natures_prophet": 4,
    "spiritbreaker": 4, "hoodwink": 4, "techies": 4,

    # Position 5 — Hard Support
    "crystal_maiden": 5, "lich": 5, "dazzle": 5, "warlock": 5,
    "shadow_demon": 5, "ogre_magi": 5, "chen": 5, "io": 5,
    "treant": 5, "oracle": 5, "bane": 5, "rubick": 5,
    "abaddon": 5, "undying": 5, "grimstroke": 5,
    "keeper_of_the_light": 5, "winter_wyvern": 5, "witch_doctor": 5,
    "jakiro": 5, "shadow_shaman": 5, "vengefulspirit": 5,
}


def get_primary_position(hero_slug: str) -> int:
    return HERO_PRIMARY_POSITION.get(hero_slug, 0)
