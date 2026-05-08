from dota_bot.models import HeroInfo

ALIASES: dict[str, str] = {
    "am": "antimage",
    "anti mage": "antimage",
    "bs": "bloodseeker",
    "cm": "crystal_maiden",
    "crystal": "crystal_maiden",
    "dk": "dragon_knight",
    "dp": "death_prophet",
    "es": "earth_spirit",
    "io": "wisp",
    "lc": "legion_commander",
    "legion": "legion_commander",
    "mk": "monkey_king",
    "ns": "night_stalker",
    "od": "obsidian_destroyer",
    "pa": "phantom_assassin",
    "pl": "phantom_lancer",
    "qop": "queenofpain",
    "queen": "queenofpain",
    "sf": "nevermore",
    "shadow fiend": "nevermore",
    "sk": "sand_king",
    "storm": "storm_spirit",
    "ss": "storm_spirit",
    "ta": "templar_assassin",
    "tb": "terrorblade",
    "wr": "windrunner",
    "windranger": "windrunner",
    "zeus": "zuus",
}


class HeroNameResolver:
    def __init__(self, heroes: list[HeroInfo]):
        self._by_slug: dict[str, HeroInfo] = {h.slug: h for h in heroes}
        self._by_name: dict[str, HeroInfo] = {}
        for h in heroes:
            self._by_name[h.localized_name.lower()] = h
            no_punct = h.localized_name.lower().replace(" ", "").replace("-", "")
            self._by_name[no_punct] = h

    def resolve(self, text: str) -> HeroInfo:
        key = text.strip().lower()
        if key in self._by_name:
            return self._by_name[key]
        normalized = key.replace(" ", "_").replace("-", "_")
        if normalized in self._by_slug:
            return self._by_slug[normalized]
        slug = ALIASES.get(key) or ALIASES.get(normalized)
        if slug and slug in self._by_slug:
            return self._by_slug[slug]
        for name, hero in self._by_name.items():
            if key in name:
                return hero
        raise ValueError(f"Hero not found: {text!r}")

    def parse_input(self, text: str) -> list[HeroInfo]:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        return [self.resolve(p) for p in parts]
