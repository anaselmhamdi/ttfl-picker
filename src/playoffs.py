"""Playoff bracket data and scarcity scoring.

Source of truth for the current NBA playoff bracket. When a round ends,
update PLAYOFF_TEAMS (remove eliminated teams, refresh odds and opponent)
and bump CURRENT_ROUND. Mirror the change into PLAYOFFS.md.
"""

from dataclasses import dataclass

from nba_api.stats.static import teams

AVG_SERIES_GAMES = 5.5
STRENGTH_EXPONENT = 1.5
ROUNDS_REMAINING_FROM = {1: 4, 2: 3, 3: 2, 4: 1}


@dataclass(frozen=True)
class PlayoffTeamInfo:
    conference: str  # "E" or "W"
    seed: int
    opponent: str  # tricode of current-series opponent
    championship_odds: int  # American odds


CURRENT_ROUND = 1

PLAYOFF_TEAMS: dict[str, PlayoffTeamInfo] = {
    # West
    "OKC": PlayoffTeamInfo("W", 1, "PHX", -110),
    "PHX": PlayoffTeamInfo("W", 8, "OKC", +75000),
    "SAS": PlayoffTeamInfo("W", 2, "POR", +600),
    "POR": PlayoffTeamInfo("W", 7, "SAS", +75000),
    "DEN": PlayoffTeamInfo("W", 3, "MIN", +1300),
    "MIN": PlayoffTeamInfo("W", 6, "DEN", +10000),
    "LAL": PlayoffTeamInfo("W", 4, "HOU", +22500),
    "HOU": PlayoffTeamInfo("W", 5, "LAL", +7500),
    # East
    "DET": PlayoffTeamInfo("E", 1, "ORL", +1600),
    "ORL": PlayoffTeamInfo("E", 8, "DET", +70000),
    "BOS": PlayoffTeamInfo("E", 2, "PHI", +600),
    "PHI": PlayoffTeamInfo("E", 7, "BOS", +25000),
    "NYK": PlayoffTeamInfo("E", 3, "ATL", +2200),
    "ATL": PlayoffTeamInfo("E", 6, "NYK", +12500),
    "CLE": PlayoffTeamInfo("E", 4, "TOR", +1300),
    "TOR": PlayoffTeamInfo("E", 5, "CLE", +25000),
}


def american_to_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def _per_round_win_prob(tricode: str) -> float:
    """Implied per-round win probability, assuming uniform round-by-round skill."""
    info = PLAYOFF_TEAMS[tricode]
    rounds = ROUNDS_REMAINING_FROM[CURRENT_ROUND]
    p_champ = max(american_to_prob(info.championship_odds), 1e-6)
    return p_champ ** (1 / rounds)


def expected_remaining_games(tricode: str) -> float:
    """Expected number of playoff games this team will play from CURRENT_ROUND onward."""
    if tricode not in PLAYOFF_TEAMS:
        return 0.0
    p = _per_round_win_prob(tricode)
    rounds_left = ROUNDS_REMAINING_FROM[CURRENT_ROUND]
    series = sum(p**i for i in range(rounds_left))
    return AVG_SERIES_GAMES * series


def _baseline_games() -> float:
    if not PLAYOFF_TEAMS:
        return 1.0
    total = sum(expected_remaining_games(t) for t in PLAYOFF_TEAMS)
    return total / len(PLAYOFF_TEAMS)


def scarcity_factor(tricode: str, strength: float = STRENGTH_EXPONENT) -> float:
    """Multiplier that boosts players on teams with fewer expected remaining games.

    baseline/games = 1 for an average team. Seed #1 (title favorite) gets <1,
    seed #8 (likely round-1 out) gets >1. Exponent controls how strong the tilt is.
    """
    if tricode not in PLAYOFF_TEAMS:
        return 0.0
    games = expected_remaining_games(tricode)
    if games <= 0:
        return 0.0
    return (_baseline_games() / games) ** strength


def is_playoff_team(tricode: str) -> bool:
    return tricode in PLAYOFF_TEAMS


def playoff_team_ids() -> set[int]:
    """NBA team_ids for every team currently in the bracket."""
    by_abbrev = {t["abbreviation"]: t["id"] for t in teams.get_teams()}
    return {by_abbrev[tc] for tc in PLAYOFF_TEAMS if tc in by_abbrev}


def elimination_tier(tricode: str) -> str:
    """Bin a team into one of four visual tiers based on championship odds.

    Bins are computed relative to the current bracket: top quarter favorites,
    next quarter contenders, next quarter longshots, bottom quarter early-outs.
    """
    if tricode not in PLAYOFF_TEAMS:
        return "unknown"
    ranked = sorted(
        PLAYOFF_TEAMS,
        key=lambda t: american_to_prob(PLAYOFF_TEAMS[t].championship_odds),
        reverse=True,
    )
    idx = ranked.index(tricode)
    quarter = len(ranked) / 4
    if idx < quarter:
        return "favorite"
    if idx < 2 * quarter:
        return "contender"
    if idx < 3 * quarter:
        return "longshot"
    return "early-out"


def tier_emoji(tier: str) -> str:
    return {
        "favorite": "🏆",
        "contender": "⭐",
        "longshot": "🎲",
        "early-out": "🪦",
    }.get(tier, "")


def get_team_info(tricode: str) -> PlayoffTeamInfo | None:
    return PLAYOFF_TEAMS.get(tricode)
