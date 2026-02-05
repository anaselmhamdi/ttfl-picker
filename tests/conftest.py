"""Shared fixtures for TTFL Picker tests."""

import pytest


@pytest.fixture
def sample_game_stats():
    """Standard NBA game stats."""
    return {
        "PTS": 25,
        "REB": 8,
        "AST": 6,
        "STL": 2,
        "BLK": 1,
        "FGM": 10,
        "FGA": 18,
        "FG3M": 3,
        "FG3A": 7,
        "FTM": 2,
        "FTA": 3,
        "TOV": 3,
    }


@pytest.fixture
def perfect_shooting_stats():
    """Perfect shooting game - no misses."""
    return {
        "PTS": 30,
        "REB": 5,
        "AST": 10,
        "STL": 3,
        "BLK": 2,
        "FGM": 12,
        "FGA": 12,  # 100% FG
        "FG3M": 4,
        "FG3A": 4,  # 100% 3PT
        "FTM": 2,
        "FTA": 2,  # 100% FT
        "TOV": 1,
    }


@pytest.fixture
def turnover_heavy_stats():
    """High turnover game."""
    return {
        "PTS": 20,
        "REB": 4,
        "AST": 8,
        "STL": 1,
        "BLK": 0,
        "FGM": 6,
        "FGA": 15,
        "FG3M": 2,
        "FG3A": 8,
        "FTM": 6,
        "FTA": 8,
        "TOV": 7,
    }


@pytest.fixture
def sample_ttfl_scores():
    """10 games of TTFL scores (most recent first)."""
    return [45, 38, 42, 35, 50, 28, 44, 39, 41, 36]


@pytest.fixture
def hot_streak_scores():
    """Scores showing upward trend (most recent first)."""
    return [55, 50, 45, 40, 35, 30, 28, 25, 22, 20]


@pytest.fixture
def cold_streak_scores():
    """Scores showing downward trend (most recent first)."""
    return [20, 25, 30, 35, 40, 45, 48, 50, 52, 55]


@pytest.fixture
def consistent_scores():
    """Low variance scores."""
    return [40, 41, 39, 40, 42, 38, 41, 40, 39, 40]


@pytest.fixture
def inconsistent_scores():
    """High variance scores."""
    return [60, 20, 55, 15, 65, 25, 50, 10, 70, 30]


@pytest.fixture
def sample_injuries():
    """Sample injury report dict."""
    return {
        "LeBron James": "Questionable",
        "Stephen Curry": "Out",
        "Kevin Durant": "Probable",
        "Giannis Antetokounmpo": "Day-To-Day",
        "Luka Doncic": "Doubtful",
    }
