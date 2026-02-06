"""Team defense statistics and TTFL defense rating calculation."""

from dataclasses import dataclass

from nba_api.stats.endpoints import LeagueDashTeamStats
from nba_api.stats.static import teams

from . import get_current_season
from .nba_config import nba_api_call


# Maximum defense adjustment
MAX_DEFENSE_ADJUSTMENT = 0.30  # +/- 30%

# Cache for team defense stats (populated once per run)
_defense_stats_cache: dict[int, "TeamDefenseStats"] | None = None


@dataclass
class TeamDefenseStats:
    """Defense statistics for a team."""

    team_id: int
    team_abbrev: str
    team_name: str
    opp_pts: float  # Points allowed per game
    opp_reb: float  # Rebounds allowed per game
    opp_ast: float  # Assists allowed per game
    opp_fgm: float  # FGM allowed per game
    opp_fg3m: float  # 3PM allowed per game
    opp_ftm: float  # FTM allowed per game
    opp_tov: float  # Turnovers forced per game
    estimated_ttfl_allowed: float  # Estimated TTFL points allowed per game
    defense_factor: float  # Factor relative to league average


def _calculate_estimated_ttfl_allowed(stats: dict) -> float:
    """
    Estimate TTFL points a defense allows per player.

    This is a rough estimate based on team-level opponent stats,
    distributed across ~5 main players.
    """
    # Get opponent stats (what the defense allows)
    opp_pts = stats.get("OPP_PTS", 0) or 0
    opp_reb = stats.get("OPP_REB", 0) or 0
    opp_ast = stats.get("OPP_AST", 0) or 0
    opp_fgm = stats.get("OPP_FGM", 0) or 0
    opp_fg3m = stats.get("OPP_FG3M", 0) or 0
    opp_ftm = stats.get("OPP_FTM", 0) or 0
    opp_tov = stats.get("OPP_TOV", 0) or 0  # Turnovers forced (negative for opponent)

    # Also need misses for negative TTFL contribution
    opp_fga = stats.get("OPP_FGA", 0) or 0
    opp_fg3a = stats.get("OPP_FG3A", 0) or 0
    opp_fta = stats.get("OPP_FTA", 0) or 0

    opp_fg_miss = opp_fga - opp_fgm
    opp_fg3_miss = opp_fg3a - opp_fg3m
    opp_ft_miss = opp_fta - opp_ftm

    # TTFL formula applied to team totals
    positive = opp_pts + opp_reb + opp_ast + opp_fgm + opp_fg3m + opp_ftm
    # Note: STL and BLK are defensive stats, so they're included in what the defense ALLOWS
    # We don't have OPP_STL and OPP_BLK in standard stats, so we estimate with typical values
    positive += 15  # Rough estimate: ~8 steals + ~5 blocks per game for opponents

    negative = opp_tov + opp_fg_miss + opp_fg3_miss + opp_ft_miss

    team_ttfl_allowed = positive - negative

    # Distribute across ~5 main rotation players for per-player estimate
    return team_ttfl_allowed / 5


def get_team_abbrev(team_id: int) -> str:
    """Get team abbreviation from team ID."""
    for team in teams.get_teams():
        if team["id"] == team_id:
            return team["abbreviation"]
    return str(team_id)


def get_team_name(team_id: int) -> str:
    """Get team full name from team ID."""
    for team in teams.get_teams():
        if team["id"] == team_id:
            return team["full_name"]
    return str(team_id)


def fetch_team_defense_stats(season: str | None = None) -> dict[int, TeamDefenseStats]:
    """
    Fetch defensive stats for all NBA teams.

    Uses LeagueDashTeamStats with MeasureType="Opponent" to get
    what each team allows on defense.

    Args:
        season: NBA season string

    Returns:
        Dict mapping team_id to TeamDefenseStats
    """
    global _defense_stats_cache

    if _defense_stats_cache is not None:
        return _defense_stats_cache

    if season is None:
        season = get_current_season()

    try:
        # Fetch opponent stats (what defenses allow)
        team_stats = nba_api_call(
            LeagueDashTeamStats,
            critical=False,
            season=season,
            measure_type_detailed_defense="Opponent",
            per_mode_detailed="PerGame",
        )
        if team_stats is None:
            print("Warning: Could not fetch team defense stats (all retries exhausted)")
            return {}
        df = team_stats.get_data_frames()[0]

        if df.empty:
            print("Warning: No team defense stats available")
            return {}

        # Calculate stats for each team
        team_defense = {}
        ttfl_allowed_values = []

        for _, row in df.iterrows():
            team_id = row["TEAM_ID"]
            stats = row.to_dict()

            estimated_ttfl = _calculate_estimated_ttfl_allowed(stats)
            ttfl_allowed_values.append(estimated_ttfl)

            team_defense[team_id] = TeamDefenseStats(
                team_id=team_id,
                team_abbrev=get_team_abbrev(team_id),
                team_name=row.get("TEAM_NAME", get_team_name(team_id)),
                opp_pts=stats.get("OPP_PTS", 0) or 0,
                opp_reb=stats.get("OPP_REB", 0) or 0,
                opp_ast=stats.get("OPP_AST", 0) or 0,
                opp_fgm=stats.get("OPP_FGM", 0) or 0,
                opp_fg3m=stats.get("OPP_FG3M", 0) or 0,
                opp_ftm=stats.get("OPP_FTM", 0) or 0,
                opp_tov=stats.get("OPP_TOV", 0) or 0,
                estimated_ttfl_allowed=estimated_ttfl,
                defense_factor=1.0,  # Will be calculated below
            )

        # Calculate league average and defense factors
        if ttfl_allowed_values:
            league_avg = sum(ttfl_allowed_values) / len(ttfl_allowed_values)

            for team_id, stats in team_defense.items():
                if league_avg > 0:
                    raw_factor = stats.estimated_ttfl_allowed / league_avg
                    # Cap the adjustment
                    capped_factor = max(
                        1.0 - MAX_DEFENSE_ADJUSTMENT,
                        min(1.0 + MAX_DEFENSE_ADJUSTMENT, raw_factor),
                    )
                    team_defense[team_id] = TeamDefenseStats(
                        team_id=stats.team_id,
                        team_abbrev=stats.team_abbrev,
                        team_name=stats.team_name,
                        opp_pts=stats.opp_pts,
                        opp_reb=stats.opp_reb,
                        opp_ast=stats.opp_ast,
                        opp_fgm=stats.opp_fgm,
                        opp_fg3m=stats.opp_fg3m,
                        opp_ftm=stats.opp_ftm,
                        opp_tov=stats.opp_tov,
                        estimated_ttfl_allowed=stats.estimated_ttfl_allowed,
                        defense_factor=capped_factor,
                    )

        _defense_stats_cache = team_defense
        return team_defense

    except Exception as e:
        print(f"Warning: Could not fetch team defense stats: {e}")
        return {}


def get_defense_factor(opponent_team_id: int, season: str | None = None) -> float:
    """
    Get the defense factor for playing against a specific team.

    Args:
        opponent_team_id: The team ID of the opponent
        season: NBA season string

    Returns:
        Defense factor (0.70 to 1.30)
        >1.0 means bad defense (boost player's expected score)
        <1.0 means good defense (reduce player's expected score)
    """
    defense_stats = fetch_team_defense_stats(season)

    if opponent_team_id in defense_stats:
        return defense_stats[opponent_team_id].defense_factor

    return 1.0  # Default to no adjustment


def clear_cache():
    """Clear the defense stats cache."""
    global _defense_stats_cache
    _defense_stats_cache = None
