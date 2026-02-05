"""Tests for TTFL score calculation."""

import pytest

from src.ttfl import calculate_ttfl, calculate_ttfl_from_game_log


class TestCalculateTTFL:
    """Tests for calculate_ttfl function."""

    def test_standard_game(self, sample_game_stats):
        """Test TTFL calculation for a standard game."""
        # PTS=25, REB=8, AST=6, STL=2, BLK=1, FGM=10, FG3M=3, FTM=2
        # Positive: 25 + 8 + 6 + 2 + 1 + 10 + 3 + 2 = 57
        # Misses: FG_MISS=8, FG3_MISS=4, FT_MISS=1, TOV=3
        # Negative: 8 + 4 + 1 + 3 = 16
        # Total: 57 - 16 = 41
        result = calculate_ttfl(sample_game_stats)
        assert result == 41

    def test_perfect_shooting(self, perfect_shooting_stats):
        """Test TTFL calculation with perfect shooting (no misses)."""
        # PTS=30, REB=5, AST=10, STL=3, BLK=2, FGM=12, FG3M=4, FTM=2
        # Positive: 30 + 5 + 10 + 3 + 2 + 12 + 4 + 2 = 68
        # Misses: 0, TOV=1
        # Negative: 0 + 0 + 0 + 1 = 1
        # Total: 68 - 1 = 67
        result = calculate_ttfl(perfect_shooting_stats)
        assert result == 67

    def test_turnover_heavy_game(self, turnover_heavy_stats):
        """Test TTFL calculation with many turnovers and misses."""
        # PTS=20, REB=4, AST=8, STL=1, BLK=0, FGM=6, FG3M=2, FTM=6
        # Positive: 20 + 4 + 8 + 1 + 0 + 6 + 2 + 6 = 47
        # Misses: FG_MISS=9, FG3_MISS=6, FT_MISS=2, TOV=7
        # Negative: 9 + 6 + 2 + 7 = 24
        # Total: 47 - 24 = 23
        result = calculate_ttfl(turnover_heavy_stats)
        assert result == 23

    def test_zero_stats(self):
        """Test TTFL calculation with all zeros."""
        stats = {
            "PTS": 0,
            "REB": 0,
            "AST": 0,
            "STL": 0,
            "BLK": 0,
            "FGM": 0,
            "FGA": 0,
            "FG3M": 0,
            "FG3A": 0,
            "FTM": 0,
            "FTA": 0,
            "TOV": 0,
        }
        result = calculate_ttfl(stats)
        assert result == 0

    def test_missing_keys(self):
        """Test TTFL calculation with missing keys (defaults to 0)."""
        stats = {"PTS": 10, "REB": 5}
        result = calculate_ttfl(stats)
        # Only PTS and REB contribute
        assert result == 15

    def test_empty_dict(self):
        """Test TTFL calculation with empty dict."""
        result = calculate_ttfl({})
        assert result == 0

    def test_none_values(self):
        """Test TTFL calculation with None values (treated as 0)."""
        stats = {
            "PTS": None,
            "REB": 10,
            "AST": None,
            "STL": 2,
            "BLK": 1,
            "FGM": 4,
            "FGA": 8,
            "FG3M": 2,
            "FG3A": 4,
            "FTM": 0,
            "FTA": 0,
            "TOV": 1,
        }
        # Positive: 0 + 10 + 0 + 2 + 1 + 4 + 2 + 0 = 19
        # Negative: 4 + 2 + 0 + 1 = 7
        # Total: 19 - 7 = 12
        result = calculate_ttfl(stats)
        assert result == 12

    def test_high_efficiency_game(self):
        """Test high-efficiency triple-double game."""
        stats = {
            "PTS": 35,
            "REB": 12,
            "AST": 15,
            "STL": 3,
            "BLK": 2,
            "FGM": 14,
            "FGA": 20,
            "FG3M": 4,
            "FG3A": 8,
            "FTM": 3,
            "FTA": 4,
            "TOV": 4,
        }
        # Positive: 35 + 12 + 15 + 3 + 2 + 14 + 4 + 3 = 88
        # Negative: 6 + 4 + 1 + 4 = 15
        # Total: 88 - 15 = 73
        result = calculate_ttfl(stats)
        assert result == 73


class TestCalculateTTFLFromGameLog:
    """Tests for calculate_ttfl_from_game_log function."""

    def test_game_log_format(self):
        """Test that game log format is properly handled."""
        game_log = {
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
        result = calculate_ttfl_from_game_log(game_log)
        assert result == 41

    def test_game_log_with_extra_fields(self):
        """Test game log with additional fields that should be ignored."""
        game_log = {
            "PTS": 20,
            "REB": 5,
            "AST": 5,
            "STL": 1,
            "BLK": 1,
            "FGM": 8,
            "FGA": 15,
            "FG3M": 2,
            "FG3A": 6,
            "FTM": 2,
            "FTA": 2,
            "TOV": 2,
            "MIN": "32:00",  # Extra field
            "PLUS_MINUS": 10,  # Extra field
            "GAME_ID": "0022300123",  # Extra field
        }
        # Positive: 20 + 5 + 5 + 1 + 1 + 8 + 2 + 2 = 44
        # Negative: 7 + 4 + 0 + 2 = 13
        # Total: 44 - 13 = 31
        result = calculate_ttfl_from_game_log(game_log)
        assert result == 31

    def test_game_log_empty(self):
        """Test empty game log."""
        result = calculate_ttfl_from_game_log({})
        assert result == 0
