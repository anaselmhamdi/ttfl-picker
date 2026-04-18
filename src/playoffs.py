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
    championship_odds: int  # American odds to win the NBA title
    series_odds: int  # American odds to win the CURRENT series


CURRENT_ROUND = 1

PLAYOFF_TEAMS: dict[str, PlayoffTeamInfo] = {
    # West
    "OKC": PlayoffTeamInfo("W", 1, "PHX", -110, -3000),
    "PHX": PlayoffTeamInfo("W", 8, "OKC", +75000, +1300),
    "SAS": PlayoffTeamInfo("W", 2, "POR", +600, -2000),
    "POR": PlayoffTeamInfo("W", 7, "SAS", +75000, +1000),
    "DEN": PlayoffTeamInfo("W", 3, "MIN", +1300, -350),
    "MIN": PlayoffTeamInfo("W", 6, "DEN", +10000, +280),
    # Rockets are favored over the Lakers (Luka + Reaves injured)
    "LAL": PlayoffTeamInfo("W", 4, "HOU", +22500, +400),
    "HOU": PlayoffTeamInfo("W", 5, "LAL", +7500, -575),
    # East
    "DET": PlayoffTeamInfo("E", 1, "ORL", +1600, -500),
    "ORL": PlayoffTeamInfo("E", 8, "DET", +70000, +380),
    "BOS": PlayoffTeamInfo("E", 2, "PHI", +600, -900),
    "PHI": PlayoffTeamInfo("E", 7, "BOS", +25000, +600),
    "NYK": PlayoffTeamInfo("E", 3, "ATL", +2200, -275),
    "ATL": PlayoffTeamInfo("E", 6, "NYK", +12500, +220),
    "CLE": PlayoffTeamInfo("E", 4, "TOR", +1300, -550),
    "TOR": PlayoffTeamInfo("E", 5, "CLE", +25000, +400),
}


def american_to_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def _current_round_win_prob(tricode: str) -> float:
    """Win probability of the current series, taken directly from series odds."""
    info = PLAYOFF_TEAMS[tricode]
    return max(american_to_prob(info.series_odds), 1e-6)


def _later_round_win_prob(tricode: str) -> float:
    """Uniform per-round win prob for rounds AFTER the current one.

    Derived residually: p_champ = p_current * q^(rounds_left - 1), solve for q.
    Clamped to [1e-6, 1] to keep the geometric series well-defined.
    """
    info = PLAYOFF_TEAMS[tricode]
    rounds_left = ROUNDS_REMAINING_FROM[CURRENT_ROUND]
    if rounds_left <= 1:
        return 0.0
    p_champ = max(american_to_prob(info.championship_odds), 1e-6)
    p_current = _current_round_win_prob(tricode)
    residual = p_champ / p_current
    # If series odds and championship odds disagree heavily, clamp.
    residual = min(max(residual, 1e-6), 1.0)
    return residual ** (1 / (rounds_left - 1))


def expected_remaining_games(tricode: str) -> float:
    """Expected number of playoff games this team will play from CURRENT_ROUND onward.

    Uses series odds for the current round (sharper) and residual championship
    odds for future rounds.
    """
    if tricode not in PLAYOFF_TEAMS:
        return 0.0
    p_current = _current_round_win_prob(tricode)
    q = _later_round_win_prob(tricode)
    rounds_left = ROUNDS_REMAINING_FROM[CURRENT_ROUND]
    # Series played = 1 (current) + p_current*1 + p_current*q + p_current*q^2 + ...
    series = 1.0
    if rounds_left > 1:
        advancement = p_current
        for i in range(rounds_left - 1):
            series += advancement
            advancement *= q
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
