"""Main recommendation logic for TTFL picks."""

from dataclasses import dataclass

from .defense_stats import get_defense_factor
from .form_analysis import FormAnalysis, analyze_form, calculate_form_score
from .injuries import get_dnp_risk, get_injury_report, get_injury_status_display, match_player_injury
from .matchups import get_defender_factor
from .nba_data import (
    get_player_ttfl_scores,
    get_players_playing_tonight,
    get_team_abbrev,
)
from .ttfl_client import get_locked_players


@dataclass
class PlayerRecommendation:
    """A player recommendation with all relevant data."""

    name: str
    team: str
    player_id: int
    opponent_team: str

    # Form analysis
    avg_ttfl: float
    weighted_avg: float
    trend_factor: float
    trend_direction: str  # "hot", "cold", "stable"
    consistency_factor: float

    # Matchup analysis
    defense_factor: float  # Team overall defense
    best_defender: str | None  # Name of best defender on opponent
    defender_factor: float  # Elite defender penalty

    # Final scoring
    adjusted_score: float
    injury_status: str | None
    dnp_risk: float
    is_locked: bool
    games_played: int = 10

    @property
    def status_display(self) -> str:
        if self.is_locked:
            return "Locked"
        return get_injury_status_display(self.injury_status)

    @property
    def is_out(self) -> bool:
        return self.dnp_risk >= 1.0

    @property
    def trend_display(self) -> str:
        """Display trend as percentage change."""
        pct = (self.trend_factor - 1.0) * 100
        if pct > 0:
            return f"+{pct:.0f}%"
        elif pct < 0:
            return f"{pct:.0f}%"
        return "0%"


def calculate_final_score(
    form_analysis: FormAnalysis,
    defense_factor: float,
    defender_factor: float,
    dnp_risk: float,
    use_form: bool = True,
    use_defense: bool = True,
) -> float:
    """
    Calculate the final risk-adjusted score.

    Formula:
    form_score = weighted_avg * trend_factor * consistency_factor
    defense_adjusted = form_score * defense_factor
    matchup_adjusted = defense_adjusted * defender_factor
    final_score = matchup_adjusted * (1 - dnp_risk)
    """
    if use_form:
        form_score = calculate_form_score(form_analysis)
    else:
        form_score = form_analysis.simple_avg

    if use_defense:
        defense_adjusted = form_score * defense_factor
        matchup_adjusted = defense_adjusted * defender_factor
    else:
        matchup_adjusted = form_score

    final_score = matchup_adjusted * (1 - dnp_risk)

    return final_score


def get_recommendations(
    cookie_file: str,
    date: str | None = None,
    top_n: int = 10,
    include_risky: bool = False,
    include_locked: bool = False,
    ignore_locks: bool = False,
    use_form: bool = True,
    use_defense: bool = True,
) -> list[PlayerRecommendation]:
    """
    Get TTFL pick recommendations for a given date.

    Args:
        cookie_file: Path to TTFL cookie file
        date: Date in YYYY-MM-DD format (default: today)
        top_n: Number of recommendations to return
        include_risky: Include players marked as OUT
        include_locked: Include locked players (for display purposes)
        ignore_locks: Skip fetching locked players (for bots/general use)
        use_form: Use form analysis (weighted avg, trend, consistency)
        use_defense: Use defense adjustments (team defense, best defender)

    Returns:
        List of PlayerRecommendation sorted by adjusted score
    """
    if ignore_locks:
        locked_players = set()
        print("Skipping lock check (--ignore-locks)")
    else:
        print("Fetching locked players from TTFL...")
        locked_players = get_locked_players(cookie_file)
        print(f"  Found {len(locked_players)} locked players")

    print("Fetching injury report...")
    injuries = get_injury_report()
    print(f"  Found {len(injuries)} players with injury status")

    print("Fetching tonight's games...")
    players, games = get_players_playing_tonight(date)
    print(f"  Found {len(players)} players in tonight's games")

    if not players:
        print("No games scheduled for this date!")
        return []

    # Pre-fetch defense stats if enabled (1 API call for all teams)
    if use_defense:
        print("Fetching team defense stats...")
        from .defense_stats import fetch_team_defense_stats

        fetch_team_defense_stats()
        print("  Team defense stats loaded")

        print("Fetching defender rankings...")
        from .matchups import fetch_defender_stats

        fetch_defender_stats()
        print("  Defender rankings loaded")

    recommendations = []
    total = len(players)

    print(f"Calculating TTFL scores for {total} players...")

    for i, player in enumerate(players, 1):
        if i % 20 == 0:
            print(f"  Progress: {i}/{total}")

        player_name = player["name"]
        player_id = player["id"]
        team = player["team"]
        opponent_team_id = player.get("opponent_team_id")
        opponent_team = get_team_abbrev(opponent_team_id) if opponent_team_id else "?"

        # Check if locked
        is_locked = player_name in locked_players or any(
            locked.lower() == player_name.lower() for locked in locked_players
        )

        # Skip locked players unless explicitly included
        if is_locked and not include_locked:
            continue

        # Get injury status
        injury_status = match_player_injury(player_name, injuries)
        dnp_risk = get_dnp_risk(injury_status)

        # Skip OUT players unless explicitly included
        if dnp_risk >= 1.0 and not include_risky:
            continue

        # Get TTFL scores for form analysis
        ttfl_scores = get_player_ttfl_scores(player_id)

        if not ttfl_scores:
            continue

        # Analyze form
        form_analysis = analyze_form(ttfl_scores)
        avg_ttfl = form_analysis.simple_avg

        # Skip players with very low average (likely bench players)
        if avg_ttfl < 10:
            continue

        # Get defense factors
        if use_defense and opponent_team_id:
            defense_factor = get_defense_factor(opponent_team_id)
            defender_factor, best_defender = get_defender_factor(opponent_team_id)
        else:
            defense_factor = 1.0
            defender_factor = 1.0
            best_defender = None

        # Calculate final score
        adjusted_score = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=defense_factor,
            defender_factor=defender_factor,
            dnp_risk=dnp_risk,
            use_form=use_form,
            use_defense=use_defense,
        )

        rec = PlayerRecommendation(
            name=player_name,
            team=team,
            player_id=player_id,
            opponent_team=opponent_team,
            avg_ttfl=avg_ttfl,
            weighted_avg=form_analysis.weighted_avg,
            trend_factor=form_analysis.trend_factor,
            trend_direction=form_analysis.trend_direction,
            consistency_factor=form_analysis.consistency_factor,
            defense_factor=defense_factor,
            best_defender=best_defender,
            defender_factor=defender_factor,
            adjusted_score=adjusted_score,
            injury_status=injury_status,
            dnp_risk=dnp_risk,
            is_locked=is_locked,
            games_played=len(ttfl_scores),
        )
        recommendations.append(rec)

    # Sort by adjusted score (highest first)
    recommendations.sort(key=lambda x: x.adjusted_score, reverse=True)

    return recommendations[:top_n]


def format_recommendations(
    recommendations: list[PlayerRecommendation],
    date: str,
    verbose: bool = False,
) -> str:
    """Format recommendations for display."""
    lines = [
        f"TTFL Picks for {date}",
        "",
    ]

    if verbose:
        lines.extend([
            "Top Recommendations (detailed breakdown):",
            "",
            f"{'#':>2}  {'Player':<20} {'Team':<4} {'vs':<4} {'Avg':>5} {'Form':>5} {'Trend':>6} {'Def':>5} {'Dfdr':>5} {'Final':>6}  Status",
            "-" * 95,
        ])

        for i, rec in enumerate(recommendations, 1):
            defender_display = f"{rec.defender_factor:.2f}" if rec.best_defender else "1.00"
            lines.append(
                f"{i:>2}  {rec.name:<20} {rec.team:<4} {rec.opponent_team:<4} "
                f"{rec.avg_ttfl:>5.1f} {rec.weighted_avg:>5.1f} {rec.trend_display:>6} "
                f"{rec.defense_factor:>5.2f} {defender_display:>5} {rec.adjusted_score:>6.1f}  {rec.status_display}"
            )

        lines.extend([
            "",
            "Column Legend:",
            "  Avg   = Simple average TTFL (last 10 games)",
            "  Form  = Weighted average (recent games weighted more)",
            "  Trend = Hot/cold trend adjustment",
            "  Def   = Team defense factor (>1 = weak defense)",
            "  Dfdr  = Best defender penalty (<1 = elite defender)",
            "  Final = Risk-adjusted final score",
        ])

        # Show best defenders info
        defenders_shown = set()
        for rec in recommendations:
            if rec.best_defender and rec.defender_factor < 1.0 and rec.best_defender not in defenders_shown:
                defenders_shown.add(rec.best_defender)

        if defenders_shown:
            lines.extend([
                "",
                "Elite/Good Defenders on Opponents:",
            ])
            for rec in recommendations:
                if rec.best_defender and rec.defender_factor < 1.0 and rec.best_defender in defenders_shown:
                    tier = "Elite" if rec.defender_factor <= 0.85 else "Good"
                    lines.append(f"  {rec.opponent_team}: {rec.best_defender} ({tier})")
                    defenders_shown.discard(rec.best_defender)

    else:
        lines.extend([
            "Top Recommendations (risk-adjusted):",
            "",
            f"{'#':>2}  {'Player':<25} {'Team':<5} {'vs':<5} {'Avg TTFL':>8} {'Adj Score':>9}  Status",
            "-" * 80,
        ])

        for i, rec in enumerate(recommendations, 1):
            trend_indicator = ""
            if rec.trend_direction == "hot":
                trend_indicator = " ^"
            elif rec.trend_direction == "cold":
                trend_indicator = " v"

            lines.append(
                f"{i:>2}  {rec.name:<25} {rec.team:<5} {rec.opponent_team:<5} "
                f"{rec.avg_ttfl:>8.1f} {rec.adjusted_score:>9.1f}{trend_indicator}  {rec.status_display}"
            )

    lines.extend([
        "",
        "Legend:",
        "  ok = Available (no injury)",
        "  ^  = Hot streak (score boosted)",
        "  v  = Cold streak (score reduced)",
        "  Questionable/Doubtful = Injury risk (score adjusted)",
        "  Locked = Picked in last 30 days",
        "",
        "Use --verbose for detailed scoring breakdown.",
    ])

    return "\n".join(lines)
