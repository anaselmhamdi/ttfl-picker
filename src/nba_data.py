"""Fetch NBA schedule and player stats via nba_api."""

import time
from datetime import datetime

import pandas as pd
from nba_api.stats.endpoints import (
    CommonTeamRoster,
    PlayerGameLog,
    ScoreboardV2,
)
from nba_api.stats.static import players, teams

from . import get_current_season
from .ttfl import calculate_ttfl_from_game_log


# Rate limiting - nba_api can be rate limited
def _rate_limit():
    time.sleep(0.6)


def get_todays_games(date: str | None = None) -> list[dict]:
    """
    Get games scheduled for a given date.

    Args:
        date: Date string in YYYY-MM-DD format. Defaults to today.

    Returns:
        List of games: [{"game_id": "...", "home_team": "LAL", "away_team": "BOS", ...}, ...]
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Convert to MM/DD/YYYY format for nba_api
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    game_date = date_obj.strftime("%m/%d/%Y")

    _rate_limit()
    scoreboard = ScoreboardV2(game_date=game_date)
    games_df = scoreboard.get_data_frames()[0]  # GameHeader

    games = []
    for _, row in games_df.iterrows():
        games.append({
            "game_id": row["GAME_ID"],
            "home_team_id": row["HOME_TEAM_ID"],
            "away_team_id": row["VISITOR_TEAM_ID"],
            "game_status": row.get("GAME_STATUS_TEXT", ""),
        })

    return games


def get_team_abbrev(team_id: int) -> str:
    """Get team abbreviation from team ID."""
    for team in teams.get_teams():
        if team["id"] == team_id:
            return team["abbreviation"]
    return str(team_id)


def get_players_for_teams(team_ids: list[int]) -> list[dict]:
    """
    Get all players from the given teams.

    Args:
        team_ids: List of NBA team IDs

    Returns:
        List of players: [{"id": 123, "name": "LeBron James", "team_id": 1610612747}, ...]
    """
    all_players = []

    for team_id in team_ids:
        _rate_limit()
        try:
            roster = CommonTeamRoster(team_id=team_id)
            roster_df = roster.get_data_frames()[0]

            for _, row in roster_df.iterrows():
                all_players.append({
                    "id": row["PLAYER_ID"],
                    "name": row["PLAYER"],
                    "team_id": team_id,
                    "team": get_team_abbrev(team_id),
                })
        except Exception as e:
            print(f"Warning: Could not fetch roster for team {team_id}: {e}")

    return all_players


def get_player_game_logs(player_id: int, season: str | None = None, last_n: int = 10) -> list[dict]:
    """
    Get recent game logs for a player.

    Args:
        player_id: NBA player ID
        season: NBA season (e.g., "2024-25")
        last_n: Number of recent games to fetch

    Returns:
        List of game stats with TTFL scores
    """
    if season is None:
        season = get_current_season()

    _rate_limit()
    try:
        game_log = PlayerGameLog(player_id=player_id, season=season)
        df = game_log.get_data_frames()[0]

        if df.empty:
            return []

        # Get last N games
        df = df.head(last_n)

        games = []
        for _, row in df.iterrows():
            game_stats = row.to_dict()
            ttfl_score = calculate_ttfl_from_game_log(game_stats)
            games.append({
                "game_date": game_stats.get("GAME_DATE"),
                "matchup": game_stats.get("MATCHUP"),
                "pts": game_stats.get("PTS"),
                "reb": game_stats.get("REB"),
                "ast": game_stats.get("AST"),
                "min": game_stats.get("MIN"),
                "ttfl_score": ttfl_score,
            })

        return games

    except Exception as e:
        print(f"Warning: Could not fetch game logs for player {player_id}: {e}")
        return []


def get_player_ttfl_scores(player_id: int, season: str | None = None, last_n: int = 10) -> list[float]:
    """
    Get list of recent TTFL scores for a player (most recent first).

    Args:
        player_id: NBA player ID
        season: NBA season (e.g., "2024-25")
        last_n: Number of recent games to fetch

    Returns:
        List of TTFL scores, most recent first
    """
    games = get_player_game_logs(player_id, season, last_n)
    return [g["ttfl_score"] for g in games if g["ttfl_score"] is not None]


def get_player_average_ttfl(player_id: int, season: str | None = None, last_n: int = 10) -> float | None:
    """
    Calculate average TTFL score for a player's recent games.

    Args:
        player_id: NBA player ID
        season: NBA season
        last_n: Number of games to average

    Returns:
        Average TTFL score or None if no data
    """
    games = get_player_game_logs(player_id, season, last_n)

    if not games:
        return None

    ttfl_scores = [g["ttfl_score"] for g in games if g["ttfl_score"] is not None]

    if not ttfl_scores:
        return None

    return sum(ttfl_scores) / len(ttfl_scores)


def find_player_id(name: str) -> int | None:
    """Find player ID by name (fuzzy match)."""
    all_players = players.get_active_players()

    # Exact match first
    for p in all_players:
        if p["full_name"].lower() == name.lower():
            return p["id"]

    # Partial match
    name_lower = name.lower()
    for p in all_players:
        if name_lower in p["full_name"].lower():
            return p["id"]

    return None


def get_opponent_team_id(player_team_id: int, games: list[dict]) -> int | None:
    """
    Get the opponent team ID for a player based on tonight's games.

    Args:
        player_team_id: The player's team ID
        games: List of games from get_todays_games()

    Returns:
        Opponent team ID, or None if team is not playing
    """
    for game in games:
        if game["home_team_id"] == player_team_id:
            return game["away_team_id"]
        elif game["away_team_id"] == player_team_id:
            return game["home_team_id"]
    return None


def get_players_playing_tonight(date: str | None = None) -> tuple[list[dict], list[dict]]:
    """
    Get all players who are playing tonight.

    Args:
        date: Date in YYYY-MM-DD format. Defaults to today.

    Returns:
        Tuple of (players, games) where:
        - players: List of players with their team info and opponent_team_id
        - games: List of games from get_todays_games()
    """
    games = get_todays_games(date)

    if not games:
        return [], []

    # Collect all team IDs
    team_ids = set()
    for game in games:
        team_ids.add(game["home_team_id"])
        team_ids.add(game["away_team_id"])

    players = get_players_for_teams(list(team_ids))

    # Add opponent team ID to each player
    for player in players:
        player["opponent_team_id"] = get_opponent_team_id(player["team_id"], games)

    return players, games
