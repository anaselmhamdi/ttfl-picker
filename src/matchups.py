"""Best defender matchup analysis."""

import time
from dataclasses import dataclass

from nba_api.stats.endpoints import LeagueDashPlayerStats
from nba_api.stats.static import teams

from . import get_current_season


# Rate limiting
def _rate_limit():
    time.sleep(0.6)


# Defender quality tiers and their factors
ELITE_DEFENDER_THRESHOLD = 20  # Top 20 defenders in NBA
GOOD_DEFENDER_THRESHOLD = 50  # Top 50 defenders

ELITE_DEFENDER_FACTOR = 0.85  # -15% penalty
GOOD_DEFENDER_FACTOR = 0.93  # -7% penalty
AVERAGE_DEFENDER_FACTOR = 1.00  # No penalty

# Cache for defender stats (populated once per run)
_defender_stats_cache: dict[int, list["DefenderStats"]] | None = None
_defender_rankings_cache: list["DefenderStats"] | None = None


@dataclass
class DefenderStats:
    """Defensive statistics for a player."""

    player_id: int
    player_name: str
    team_id: int
    team_abbrev: str
    defensive_rating: float  # Lower is better for defense
    defensive_ws: float  # Defensive Win Shares
    stl: float  # Steals per game
    blk: float  # Blocks per game
    composite_score: float  # Combined defensive score (higher = better defender)
    league_rank: int  # Rank among all players


def get_team_abbrev(team_id: int) -> str:
    """Get team abbreviation from team ID."""
    for team in teams.get_teams():
        if team["id"] == team_id:
            return team["abbreviation"]
    return str(team_id)


def _calculate_composite_score(stats: dict) -> float:
    """
    Calculate a composite defensive score for ranking defenders.

    Higher score = better defender.

    Components:
    - Inverted defensive rating (lower DRTG = better)
    - Defensive Win Shares
    - Steals + Blocks
    """
    # Defensive rating (lower is better, typical range: 100-120)
    # Invert so higher = better, normalize around 110
    drtg = stats.get("DEF_RATING", 110) or 110
    drtg_score = max(0, (120 - drtg) / 20)  # 0-1 scale, 100 DRTG = 1.0

    # Defensive Win Shares (higher is better, typical range: 0-0.15 per game estimate)
    dws = stats.get("DEF_WS", 0) or 0
    # DWS is season total, approximate to per-game value
    games = stats.get("GP", 1) or 1
    dws_per_game = dws / games if games > 0 else 0
    dws_score = min(1.0, dws_per_game / 0.1)  # 0-1 scale

    # Steals + Blocks (higher is better)
    stl = stats.get("STL", 0) or 0
    blk = stats.get("BLK", 0) or 0
    stl_blk_score = min(1.0, (stl + blk) / 3)  # 0-1 scale, 3+ stl+blk = max

    # Weighted composite
    composite = (drtg_score * 0.4) + (dws_score * 0.3) + (stl_blk_score * 0.3)

    return composite


def fetch_defender_stats(season: str | None = None) -> tuple[dict[int, list[DefenderStats]], list[DefenderStats]]:
    """
    Fetch defensive stats for all NBA players.

    Returns:
        Tuple of:
        - Dict mapping team_id to list of defenders on that team
        - List of all defenders ranked by composite score
    """
    global _defender_stats_cache, _defender_rankings_cache

    if _defender_stats_cache is not None and _defender_rankings_cache is not None:
        return _defender_stats_cache, _defender_rankings_cache

    if season is None:
        season = get_current_season()

    _rate_limit()

    try:
        # Fetch player defense stats
        player_stats = LeagueDashPlayerStats(
            season=season,
            measure_type_detailed_defense="Defense",
            per_mode_detailed="PerGame",
        )
        df = player_stats.get_data_frames()[0]

        if df.empty:
            print("Warning: No player defense stats available")
            return {}, []

        # Build defender list with composite scores
        all_defenders = []

        for _, row in df.iterrows():
            stats = row.to_dict()

            # Skip players with minimal playing time
            min_played = stats.get("MIN", 0) or 0
            if min_played < 15:  # Less than 15 min/game
                continue

            composite = _calculate_composite_score(stats)

            defender = DefenderStats(
                player_id=row["PLAYER_ID"],
                player_name=row["PLAYER_NAME"],
                team_id=row["TEAM_ID"],
                team_abbrev=get_team_abbrev(row["TEAM_ID"]),
                defensive_rating=stats.get("DEF_RATING", 110) or 110,
                defensive_ws=stats.get("DEF_WS", 0) or 0,
                stl=stats.get("STL", 0) or 0,
                blk=stats.get("BLK", 0) or 0,
                composite_score=composite,
                league_rank=0,  # Will be set after sorting
            )
            all_defenders.append(defender)

        # Sort by composite score (highest = best defender)
        all_defenders.sort(key=lambda x: x.composite_score, reverse=True)

        # Assign league ranks
        for i, defender in enumerate(all_defenders):
            all_defenders[i] = DefenderStats(
                player_id=defender.player_id,
                player_name=defender.player_name,
                team_id=defender.team_id,
                team_abbrev=defender.team_abbrev,
                defensive_rating=defender.defensive_rating,
                defensive_ws=defender.defensive_ws,
                stl=defender.stl,
                blk=defender.blk,
                composite_score=defender.composite_score,
                league_rank=i + 1,
            )

        # Group by team
        team_defenders: dict[int, list[DefenderStats]] = {}
        for defender in all_defenders:
            if defender.team_id not in team_defenders:
                team_defenders[defender.team_id] = []
            team_defenders[defender.team_id].append(defender)

        _defender_stats_cache = team_defenders
        _defender_rankings_cache = all_defenders

        return team_defenders, all_defenders

    except Exception as e:
        print(f"Warning: Could not fetch defender stats: {e}")
        return {}, []


def get_best_defender(opponent_team_id: int, season: str | None = None) -> DefenderStats | None:
    """
    Get the best defender on a specific team.

    Args:
        opponent_team_id: The team ID to find the best defender for
        season: NBA season string

    Returns:
        DefenderStats for the best defender, or None if not found
    """
    team_defenders, _ = fetch_defender_stats(season)

    if opponent_team_id in team_defenders and team_defenders[opponent_team_id]:
        # Return the first defender (already sorted by composite score)
        return team_defenders[opponent_team_id][0]

    return None


def get_defender_factor(opponent_team_id: int, season: str | None = None) -> tuple[float, str | None]:
    """
    Get the defender factor for playing against a specific team.

    Args:
        opponent_team_id: The team ID of the opponent
        season: NBA season string

    Returns:
        Tuple of (defender_factor, best_defender_name)
        - defender_factor: 0.85 to 1.0
        - best_defender_name: Name of the best defender, or None
    """
    best_defender = get_best_defender(opponent_team_id, season)

    if best_defender is None:
        return AVERAGE_DEFENDER_FACTOR, None

    # Determine factor based on league rank
    if best_defender.league_rank <= ELITE_DEFENDER_THRESHOLD:
        factor = ELITE_DEFENDER_FACTOR
    elif best_defender.league_rank <= GOOD_DEFENDER_THRESHOLD:
        factor = GOOD_DEFENDER_FACTOR
    else:
        factor = AVERAGE_DEFENDER_FACTOR

    return factor, best_defender.player_name


def clear_cache():
    """Clear the defender stats cache."""
    global _defender_stats_cache, _defender_rankings_cache
    _defender_stats_cache = None
    _defender_rankings_cache = None
