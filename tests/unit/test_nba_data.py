"""Tests for NBA data functions."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.nba_data import get_earliest_game_time


class TestGetEarliestGameTime:
    """Tests for get_earliest_game_time function."""

    def test_finds_earliest_time(self):
        """Test finding earliest game time from multiple games."""
        tz_est = ZoneInfo("America/New_York")
        games = [
            {"game_id": "1", "game_time_utc": datetime(2025, 2, 5, 19, 0, tzinfo=tz_est)},  # 7pm
            {"game_id": "2", "game_time_utc": datetime(2025, 2, 5, 21, 30, tzinfo=tz_est)},  # 9:30pm
            {"game_id": "3", "game_time_utc": datetime(2025, 2, 5, 20, 0, tzinfo=tz_est)},  # 8pm
        ]
        result = get_earliest_game_time(games)
        assert result is not None
        # 7pm EST = 1am Paris next day
        assert result.tzinfo == ZoneInfo("Europe/Paris")
        assert result.hour == 1  # 7pm EST = 1am Paris

    def test_returns_none_for_empty_list(self):
        """Test returns None when no games provided."""
        assert get_earliest_game_time([]) is None

    def test_returns_none_for_no_times(self):
        """Test returns None when games have no time data."""
        games = [
            {"game_id": "1", "game_time_utc": None},
            {"game_id": "2"},
        ]
        assert get_earliest_game_time(games) is None

    def test_single_game(self):
        """Test with single game."""
        tz_est = ZoneInfo("America/New_York")
        games = [
            {"game_id": "1", "game_time_utc": datetime(2025, 2, 5, 19, 30, tzinfo=tz_est)},
        ]
        result = get_earliest_game_time(games)
        assert result is not None
        assert result.tzinfo == ZoneInfo("Europe/Paris")

    def test_mixed_games_with_and_without_times(self):
        """Test handles mix of games with and without times."""
        tz_est = ZoneInfo("America/New_York")
        games = [
            {"game_id": "1", "game_time_utc": None},
            {"game_id": "2", "game_time_utc": datetime(2025, 2, 5, 22, 0, tzinfo=tz_est)},
            {"game_id": "3"},
        ]
        result = get_earliest_game_time(games)
        assert result is not None
