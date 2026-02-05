"""Integration tests for the picker module."""

import pytest
from unittest.mock import patch, MagicMock

from src.picker import get_recommendations, PlayerRecommendation
from src.form_analysis import FormAnalysis


class TestGetRecommendationsIntegration:
    """Integration tests for get_recommendations with mocked external calls."""

    @pytest.fixture
    def mock_locked_players(self):
        """Mock locked players set."""
        return {"Damian Lillard", "Devin Booker"}

    @pytest.fixture
    def mock_injuries(self):
        """Mock injury report."""
        return {
            "LeBron James": "Questionable",
            "Stephen Curry": "Out",
            "Kevin Durant": "Probable",
        }

    @pytest.fixture
    def mock_players(self):
        """Mock players playing tonight."""
        return [
            {
                "name": "LeBron James",
                "id": 2544,
                "team": "LAL",
                "opponent_team_id": 1610612744,  # GSW
            },
            {
                "name": "Stephen Curry",
                "id": 201939,
                "team": "GSW",
                "opponent_team_id": 1610612747,  # LAL
            },
            {
                "name": "Kevin Durant",
                "id": 201142,
                "team": "PHX",
                "opponent_team_id": 1610612743,  # DEN
            },
            {
                "name": "Nikola Jokic",
                "id": 203999,
                "team": "DEN",
                "opponent_team_id": 1610612756,  # PHX
            },
            {
                "name": "Damian Lillard",
                "id": 203081,
                "team": "MIL",
                "opponent_team_id": 1610612751,  # BKN
            },
        ]

    @pytest.fixture
    def mock_games(self):
        """Mock games for tonight."""
        return [
            {"gameId": "0022300123", "homeTeam": "LAL", "awayTeam": "GSW"},
            {"gameId": "0022300124", "homeTeam": "DEN", "awayTeam": "PHX"},
            {"gameId": "0022300125", "homeTeam": "MIL", "awayTeam": "BKN"},
        ]

    @pytest.fixture
    def mock_ttfl_scores(self):
        """Mock TTFL scores for players."""
        return {
            2544: [45, 42, 48, 38, 50, 44, 41, 47, 43, 46],  # LeBron
            201939: [52, 48, 55, 45, 50, 47, 53, 49, 51, 46],  # Curry
            201142: [48, 44, 50, 42, 46, 43, 49, 45, 47, 44],  # Durant
            203999: [58, 55, 62, 52, 60, 54, 57, 59, 56, 53],  # Jokic
            203081: [42, 38, 45, 36, 40, 37, 43, 39, 41, 38],  # Lillard
        }

    def _get_ttfl_scores(self, player_id, mock_ttfl_scores):
        """Helper to get TTFL scores by player_id."""
        return mock_ttfl_scores.get(player_id, [])

    @patch("src.matchups.fetch_defender_stats")
    @patch("src.defense_stats.fetch_team_defense_stats")
    @patch("src.picker.get_defender_factor")
    @patch("src.picker.get_defense_factor")
    @patch("src.picker.get_player_ttfl_scores")
    @patch("src.picker.get_players_playing_tonight")
    @patch("src.picker.get_injury_report")
    @patch("src.picker.get_locked_players")
    def test_full_pipeline(
        self,
        mock_get_locked,
        mock_get_injuries,
        mock_get_players,
        mock_get_ttfl,
        mock_get_defense_factor,
        mock_get_defender_factor,
        mock_fetch_defense_stats,
        mock_fetch_defender_stats,
        mock_locked_players,
        mock_injuries,
        mock_players,
        mock_games,
        mock_ttfl_scores,
    ):
        """Test the full recommendation pipeline with all mocks."""
        # Setup mocks
        mock_get_locked.return_value = mock_locked_players
        mock_get_injuries.return_value = mock_injuries
        mock_get_players.return_value = (mock_players, mock_games)
        mock_get_ttfl.side_effect = lambda pid: mock_ttfl_scores.get(pid, [])
        mock_get_defense_factor.return_value = 1.0
        mock_get_defender_factor.return_value = (1.0, None)

        # Call get_recommendations
        recommendations = get_recommendations(
            cookie_file="dummy_cookies.txt",
            date="2025-01-25",
            top_n=10,
            include_risky=False,
            include_locked=False,
        )

        # Verify results
        assert len(recommendations) > 0

        # Curry should be excluded (Out)
        player_names = [r.name for r in recommendations]
        assert "Stephen Curry" not in player_names

        # Lillard should be excluded (locked)
        assert "Damian Lillard" not in player_names

        # Jokic should be included and likely top ranked
        assert "Nikola Jokic" in player_names

        # LeBron should be included but with injury penalty
        assert "LeBron James" in player_names
        lebron = next(r for r in recommendations if r.name == "LeBron James")
        assert lebron.dnp_risk == 0.40

    @patch("src.matchups.fetch_defender_stats")
    @patch("src.defense_stats.fetch_team_defense_stats")
    @patch("src.picker.get_defender_factor")
    @patch("src.picker.get_defense_factor")
    @patch("src.picker.get_player_ttfl_scores")
    @patch("src.picker.get_players_playing_tonight")
    @patch("src.picker.get_injury_report")
    @patch("src.picker.get_locked_players")
    def test_include_locked(
        self,
        mock_get_locked,
        mock_get_injuries,
        mock_get_players,
        mock_get_ttfl,
        mock_get_defense_factor,
        mock_get_defender_factor,
        mock_fetch_defense_stats,
        mock_fetch_defender_stats,
        mock_locked_players,
        mock_injuries,
        mock_players,
        mock_games,
        mock_ttfl_scores,
    ):
        """Test including locked players in recommendations."""
        # Setup mocks
        mock_get_locked.return_value = mock_locked_players
        mock_get_injuries.return_value = mock_injuries
        mock_get_players.return_value = (mock_players, mock_games)
        mock_get_ttfl.side_effect = lambda pid: mock_ttfl_scores.get(pid, [])
        mock_get_defense_factor.return_value = 1.0
        mock_get_defender_factor.return_value = (1.0, None)

        recommendations = get_recommendations(
            cookie_file="dummy_cookies.txt",
            date="2025-01-25",
            top_n=10,
            include_locked=True,
        )

        # Lillard should be included with is_locked=True
        player_names = [r.name for r in recommendations]
        assert "Damian Lillard" in player_names
        lillard = next(r for r in recommendations if r.name == "Damian Lillard")
        assert lillard.is_locked is True

    @patch("src.matchups.fetch_defender_stats")
    @patch("src.defense_stats.fetch_team_defense_stats")
    @patch("src.picker.get_defender_factor")
    @patch("src.picker.get_defense_factor")
    @patch("src.picker.get_player_ttfl_scores")
    @patch("src.picker.get_players_playing_tonight")
    @patch("src.picker.get_injury_report")
    @patch("src.picker.get_locked_players")
    def test_include_risky(
        self,
        mock_get_locked,
        mock_get_injuries,
        mock_get_players,
        mock_get_ttfl,
        mock_get_defense_factor,
        mock_get_defender_factor,
        mock_fetch_defense_stats,
        mock_fetch_defender_stats,
        mock_locked_players,
        mock_injuries,
        mock_players,
        mock_games,
        mock_ttfl_scores,
    ):
        """Test including risky (OUT) players in recommendations."""
        # Setup mocks
        mock_get_locked.return_value = mock_locked_players
        mock_get_injuries.return_value = mock_injuries
        mock_get_players.return_value = (mock_players, mock_games)
        mock_get_ttfl.side_effect = lambda pid: mock_ttfl_scores.get(pid, [])
        mock_get_defense_factor.return_value = 1.0
        mock_get_defender_factor.return_value = (1.0, None)

        recommendations = get_recommendations(
            cookie_file="dummy_cookies.txt",
            date="2025-01-25",
            top_n=10,
            include_risky=True,
        )

        # Curry should be included with dnp_risk=1.0
        player_names = [r.name for r in recommendations]
        assert "Stephen Curry" in player_names
        curry = next(r for r in recommendations if r.name == "Stephen Curry")
        assert curry.dnp_risk == 1.0
        assert curry.adjusted_score == 0.0

    @patch("src.matchups.fetch_defender_stats")
    @patch("src.defense_stats.fetch_team_defense_stats")
    @patch("src.picker.get_defender_factor")
    @patch("src.picker.get_defense_factor")
    @patch("src.picker.get_player_ttfl_scores")
    @patch("src.picker.get_players_playing_tonight")
    @patch("src.picker.get_injury_report")
    def test_ignore_locks(
        self,
        mock_get_injuries,
        mock_get_players,
        mock_get_ttfl,
        mock_get_defense_factor,
        mock_get_defender_factor,
        mock_fetch_defense_stats,
        mock_fetch_defender_stats,
        mock_injuries,
        mock_players,
        mock_games,
        mock_ttfl_scores,
    ):
        """Test that ignore_locks skips fetching locked players."""
        # Setup mocks (no mock for get_locked_players)
        mock_get_injuries.return_value = mock_injuries
        mock_get_players.return_value = (mock_players, mock_games)
        mock_get_ttfl.side_effect = lambda pid: mock_ttfl_scores.get(pid, [])
        mock_get_defense_factor.return_value = 1.0
        mock_get_defender_factor.return_value = (1.0, None)

        recommendations = get_recommendations(
            cookie_file="dummy_cookies.txt",
            date="2025-01-25",
            top_n=10,
            ignore_locks=True,
        )

        # All non-OUT players should be available
        player_names = [r.name for r in recommendations]
        assert "Damian Lillard" in player_names
        lillard = next(r for r in recommendations if r.name == "Damian Lillard")
        assert lillard.is_locked is False

    @patch("src.picker.get_locked_players")
    @patch("src.picker.get_injury_report")
    @patch("src.picker.get_players_playing_tonight")
    def test_no_games_returns_empty(
        self,
        mock_get_players,
        mock_get_injuries,
        mock_get_locked,
    ):
        """Test that no games returns empty recommendations."""
        mock_get_locked.return_value = set()
        mock_get_injuries.return_value = {}
        mock_get_players.return_value = ([], [])

        recommendations = get_recommendations(
            cookie_file="dummy_cookies.txt",
            date="2025-01-25",
            top_n=10,
        )

        assert len(recommendations) == 0

    @patch("src.matchups.fetch_defender_stats")
    @patch("src.defense_stats.fetch_team_defense_stats")
    @patch("src.picker.get_defender_factor")
    @patch("src.picker.get_defense_factor")
    @patch("src.picker.get_player_ttfl_scores")
    @patch("src.picker.get_players_playing_tonight")
    @patch("src.picker.get_injury_report")
    @patch("src.picker.get_locked_players")
    def test_recommendations_sorted_by_score(
        self,
        mock_get_locked,
        mock_get_injuries,
        mock_get_players,
        mock_get_ttfl,
        mock_get_defense_factor,
        mock_get_defender_factor,
        mock_fetch_defense_stats,
        mock_fetch_defender_stats,
        mock_players,
        mock_games,
        mock_ttfl_scores,
    ):
        """Test that recommendations are sorted by adjusted score."""
        mock_get_locked.return_value = set()
        mock_get_injuries.return_value = {}
        mock_get_players.return_value = (mock_players, mock_games)
        mock_get_ttfl.side_effect = lambda pid: mock_ttfl_scores.get(pid, [])
        mock_get_defense_factor.return_value = 1.0
        mock_get_defender_factor.return_value = (1.0, None)

        recommendations = get_recommendations(
            cookie_file="dummy_cookies.txt",
            date="2025-01-25",
            top_n=10,
        )

        # Verify sorted by adjusted_score descending
        scores = [r.adjusted_score for r in recommendations]
        assert scores == sorted(scores, reverse=True)

    @patch("src.matchups.fetch_defender_stats")
    @patch("src.defense_stats.fetch_team_defense_stats")
    @patch("src.picker.get_defender_factor")
    @patch("src.picker.get_defense_factor")
    @patch("src.picker.get_player_ttfl_scores")
    @patch("src.picker.get_players_playing_tonight")
    @patch("src.picker.get_injury_report")
    @patch("src.picker.get_locked_players")
    def test_top_n_limit(
        self,
        mock_get_locked,
        mock_get_injuries,
        mock_get_players,
        mock_get_ttfl,
        mock_get_defense_factor,
        mock_get_defender_factor,
        mock_fetch_defense_stats,
        mock_fetch_defender_stats,
        mock_players,
        mock_games,
        mock_ttfl_scores,
    ):
        """Test that top_n limits the number of recommendations."""
        mock_get_locked.return_value = set()
        mock_get_injuries.return_value = {}
        mock_get_players.return_value = (mock_players, mock_games)
        mock_get_ttfl.side_effect = lambda pid: mock_ttfl_scores.get(pid, [])
        mock_get_defense_factor.return_value = 1.0
        mock_get_defender_factor.return_value = (1.0, None)

        recommendations = get_recommendations(
            cookie_file="dummy_cookies.txt",
            date="2025-01-25",
            top_n=2,
        )

        assert len(recommendations) <= 2
