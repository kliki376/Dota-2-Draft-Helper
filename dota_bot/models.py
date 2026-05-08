from dataclasses import dataclass, field


@dataclass
class HeroInfo:
    id: int
    slug: str           # "crystal_maiden" (npc_dota_hero_ prefix stripped)
    localized_name: str # "Crystal Maiden"


@dataclass
class HeroMatchup:
    hero_slug: str
    advantage: float    # positive = we counter them (win_rate - 0.5)
    win_rate: float     # candidate's win_rate vs this hero (0.0–1.0)


@dataclass
class HeroMeta:
    hero_id: int
    hero_slug: str
    win_rate: float     # high-bracket pub winrate (0.0–1.0)
    pick_rate: float    # normalized 0.0–1.0 relative to most-picked hero
    pro_pick: int
    pro_win: int


@dataclass
class PlayerHeroStats:
    hero_id: int
    hero_slug: str
    games: int
    wins: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games > 0 else 0.0


@dataclass
class HeroScore:
    hero_slug: str
    localized_name: str
    score: float            # 0–100 final score
    counter_score: float    # 0–100
    meta_score: float       # 0–100
    pro_score: float        # 0–100
    player_games: int = 0
    player_win_rate: float = 0.0
    matchup_details: list[HeroMatchup] = field(default_factory=list)
