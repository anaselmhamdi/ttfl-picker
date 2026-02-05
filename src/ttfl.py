"""TTFL score calculation from NBA box score stats."""


def calculate_ttfl(stats: dict) -> int:
    """
    Calculate TTFL score from player stats.

    Formula:
    PTS + REB + AST + STL + BLK + FGM + 3PM + FTM
    - (TO + FG_MISS + 3P_MISS + FT_MISS)

    Args:
        stats: Dict with keys like PTS, REB, AST, STL, BLK, FGM, FGA, FG3M, FG3A, FTM, FTA, TOV

    Returns:
        TTFL score as integer
    """
    # Positive contributions
    pts = stats.get("PTS", 0) or 0
    reb = stats.get("REB", 0) or 0
    ast = stats.get("AST", 0) or 0
    stl = stats.get("STL", 0) or 0
    blk = stats.get("BLK", 0) or 0
    fgm = stats.get("FGM", 0) or 0
    fg3m = stats.get("FG3M", 0) or 0
    ftm = stats.get("FTM", 0) or 0

    # Negative contributions (misses and turnovers)
    fga = stats.get("FGA", 0) or 0
    fg3a = stats.get("FG3A", 0) or 0
    fta = stats.get("FTA", 0) or 0
    tov = stats.get("TOV", 0) or 0

    fg_miss = fga - fgm
    fg3_miss = fg3a - fg3m
    ft_miss = fta - ftm

    positive = pts + reb + ast + stl + blk + fgm + fg3m + ftm
    negative = tov + fg_miss + fg3_miss + ft_miss

    return positive - negative


def calculate_ttfl_from_game_log(game_log: dict) -> int:
    """
    Calculate TTFL from nba_api game log format.

    The game log from nba_api has slightly different column names.
    """
    # Map nba_api column names to our expected format
    stats = {
        "PTS": game_log.get("PTS"),
        "REB": game_log.get("REB"),
        "AST": game_log.get("AST"),
        "STL": game_log.get("STL"),
        "BLK": game_log.get("BLK"),
        "FGM": game_log.get("FGM"),
        "FGA": game_log.get("FGA"),
        "FG3M": game_log.get("FG3M"),
        "FG3A": game_log.get("FG3A"),
        "FTM": game_log.get("FTM"),
        "FTA": game_log.get("FTA"),
        "TOV": game_log.get("TOV"),
    }
    return calculate_ttfl(stats)
