"""TTFL Session - centralized data fetching and caching."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .defense_stats import fetch_team_defense_stats, get_defense_factor
from .form_analysis import analyze_form
from .injuries import get_dnp_risk, get_injury_report, match_player_injury
from .matchups import fetch_defender_stats, get_defender_factor
from .nba_data import get_player_ttfl_scores, get_players_playing_tonight, get_team_abbrev
from .picker import PlayerRecommendation, calculate_final_score
from .ttfl_client import get_locked_players


@dataclass
class DayPlan:
    """Recommended pick for a single day."""

    date: str
    recommendation: PlayerRecommendation
    alternatives: list[PlayerRecommendation]


class TTFLSession:
    """
    Manages data fetching and caching for TTFL recommendations.

    Creates one session, fetches shared data once, then call methods
    for recommendations or planning.
    """

    def __init__(
        self,
        cookie_file: str = "fantasy.trashtalk.co_cookies.txt",
        ignore_locks: bool = False,
        verbose: bool = True,
    ):
        """
        Initialize session and fetch all shared data.

        Args:
            cookie_file: Path to TTFL cookie file
            ignore_locks: Skip fetching locked players
            verbose: Print progress messages
        """
        self.cookie_file = cookie_file
        self.ignore_locks = ignore_locks
        self.verbose = verbose

        # Caches
        self._locked_players: set[str] = set()
        self._injuries: dict[str, str] = {}
        self._ttfl_cache: dict[int, list[float]] = {}
        self._players_cache: dict[str, tuple[list, list]] = {}  # date -> (players, games)

        # Fetch shared data
        self._fetch_shared_data()

    def _log(self, msg: str):
        """Print if verbose mode."""
        if self.verbose:
            print(msg)

    def _fetch_shared_data(self):
        """Fetch all data that doesn't change day-to-day."""
        # Locked players
        if self.ignore_locks:
            self._locked_players = set()
            self._log("Skipping lock check (--ignore-locks)")
        else:
            self._log("Fetching locked players from TTFL...")
            self._locked_players = get_locked_players(self.cookie_file)
            self._log(f"  Found {len(self._locked_players)} locked players")

        # Injury report
        self._log("Fetching injury report...")
        self._injuries = get_injury_report()
        self._log(f"  Found {len(self._injuries)} players with injury status")

        # Defense stats (these cache globally in their modules)
        self._log("Fetching team defense stats...")
        defense_stats = fetch_team_defense_stats()
        if defense_stats:
            self._log(f"  Team defense stats loaded ({len(defense_stats)} teams)")
        else:
            self._log("  Warning: Team defense stats unavailable (will use neutral factors)")

        self._log("Fetching defender rankings...")
        team_defenders, all_defenders = fetch_defender_stats()
        if all_defenders:
            self._log(f"  Defender rankings loaded ({len(all_defenders)} players)")
        else:
            self._log("  Warning: Defender rankings unavailable (will use neutral factors)")

    def get_player_ttfl(self, player_id: int) -> list[float]:
        """Get player TTFL scores with caching."""
        if player_id not in self._ttfl_cache:
            self._ttfl_cache[player_id] = get_player_ttfl_scores(player_id)
        return self._ttfl_cache[player_id]

    def get_players_for_date(self, date: str | None = None) -> tuple[list, list]:
        """Get players and games for a date with caching."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        if date not in self._players_cache:
            self._players_cache[date] = get_players_playing_tonight(date)

        return self._players_cache[date]

    def get_recommendations(
        self,
        date: str | None = None,
        top_n: int = 10,
        include_risky: bool = False,
        include_locked: bool = False,
        use_form: bool = True,
        use_defense: bool = True,
        extra_locks: set[str] | None = None,
    ) -> list[PlayerRecommendation]:
        """
        Get TTFL pick recommendations for a given date.

        Args:
            date: Date in YYYY-MM-DD format (default: today)
            top_n: Number of recommendations to return
            include_risky: Include players marked as OUT
            include_locked: Include locked players (for display purposes)
            use_form: Use form analysis (weighted avg, trend, consistency)
            use_defense: Use defense adjustments
            extra_locks: Additional locked players (for planning simulation)

        Returns:
            List of PlayerRecommendation sorted by adjusted score
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        players, games = self.get_players_for_date(date)

        if not players:
            return []

        # Combine real locks with any extra locks (for planning)
        all_locked = self._locked_players.copy()
        if extra_locks:
            all_locked |= extra_locks

        recommendations = []
        total = len(players)

        self._log(f"Calculating TTFL scores for {total} players...")

        for i, player in enumerate(players, 1):
            if i % 50 == 0:
                self._log(f"  Progress: {i}/{total}")

            player_name = player["name"]
            player_id = player["id"]
            team = player["team"]
            opponent_team_id = player.get("opponent_team_id")
            opponent_team = get_team_abbrev(opponent_team_id) if opponent_team_id else "?"

            # Check if locked
            is_locked = player_name in all_locked or any(
                locked.lower() == player_name.lower() for locked in all_locked
            )

            # Skip locked players unless explicitly included
            if is_locked and not include_locked:
                continue

            # Get injury status
            injury_status = match_player_injury(player_name, self._injuries)
            dnp_risk = get_dnp_risk(injury_status)

            # Skip OUT players unless explicitly included
            if dnp_risk >= 1.0 and not include_risky:
                continue

            # Get TTFL scores (cached)
            ttfl_scores = self.get_player_ttfl(player_id)

            if not ttfl_scores:
                continue

            # Analyze form
            form_analysis = analyze_form(ttfl_scores)
            avg_ttfl = form_analysis.simple_avg

            # Skip players with very low average
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

    def plan_picks(self, days: int = 7) -> list[DayPlan]:
        """
        Plan optimal picks for the next N days.

        Simulates picking the top available player each day,
        then locking them for subsequent days.

        Args:
            days: Number of days to plan

        Returns:
            List of DayPlan with recommended pick for each day
        """
        simulated_locks: set[str] = set()
        plans = []
        today = datetime.now()

        for day_offset in range(days):
            current_date = today + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            self._log(f"\n📅 Planning for {date_str}...")

            # Get recommendations excluding simulated locks
            day_recommendations = self.get_recommendations(
                date=date_str,
                top_n=20,
                extra_locks=simulated_locks,
            )

            if not day_recommendations:
                self._log(f"  ⚠️ No games or recommendations for {date_str}")
                continue

            # Pick the top recommendation
            top_pick = day_recommendations[0]
            alternatives = day_recommendations[1:4]

            # Add to simulated locks for future days
            simulated_locks.add(top_pick.name)

            plans.append(DayPlan(
                date=date_str,
                recommendation=top_pick,
                alternatives=alternatives,
            ))

            self._log(f"  ✓ Recommended: {top_pick.name} ({top_pick.team}) - {top_pick.adjusted_score:.1f} pts")

        return plans


def format_plan(plans: list[DayPlan]) -> str:
    """Format the multi-day plan for display."""
    if not plans:
        return "No picks planned - no games found for the requested dates."

    lines = [
        "📅 TTFL Pick Plan",
        "=" * 60,
        "",
    ]

    total_expected = 0

    for plan in plans:
        rec = plan.recommendation

        # Trend indicator
        if rec.trend_direction == "hot":
            trend = "🔥"
        elif rec.trend_direction == "cold":
            trend = "❄️"
        else:
            trend = ""

        # Risk indicator
        if rec.dnp_risk > 0:
            risk = f" ⚠️ {rec.injury_status}"
        else:
            risk = ""

        lines.append(f"📆 {plan.date}")
        lines.append(f"   ➤ {rec.name} ({rec.team} vs {rec.opponent_team}) {trend}")
        lines.append(f"     Expected: {rec.adjusted_score:.1f} pts | Avg: {rec.avg_ttfl:.1f}{risk}")

        if plan.alternatives:
            alt_names = ", ".join(f"{a.name} ({a.adjusted_score:.0f})" for a in plan.alternatives[:3])
            lines.append(f"     Alternatives: {alt_names}")

        lines.append("")
        total_expected += rec.adjusted_score

    lines.extend([
        "-" * 60,
        f"📊 Total Expected: {total_expected:.1f} pts over {len(plans)} days",
        f"📈 Average per day: {total_expected / len(plans):.1f} pts",
        "",
        "Note: Injury status may change. Check daily before picking.",
    ])

    return "\n".join(lines)
