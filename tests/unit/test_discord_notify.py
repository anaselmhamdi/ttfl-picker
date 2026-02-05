"""Tests for Discord notification functions."""

import pytest

from src.discord_notify import (
    _format_compact_pick,
    _format_detailed_pick,
    _generate_full_rankings_file,
    _get_matchup_emoji,
    _get_risk_emoji,
    _get_trend_emoji,
)
from src.picker import PlayerRecommendation


class TestGetMatchupEmoji:
    """Tests for _get_matchup_emoji function."""

    def test_great_matchup(self):
        """Test great matchup emoji (weak defense)."""
        assert _get_matchup_emoji(1.15, 1.0) == "🟢"

    def test_neutral_matchup(self):
        """Test neutral matchup emoji."""
        assert _get_matchup_emoji(1.0, 1.0) == "🟡"

    def test_tough_matchup(self):
        """Test tough matchup emoji."""
        assert _get_matchup_emoji(0.95, 0.98) == "🟠"

    def test_very_tough_matchup(self):
        """Test very tough matchup emoji (elite defense + defender)."""
        assert _get_matchup_emoji(0.90, 0.85) == "🔴"


class TestGetTrendEmoji:
    """Tests for _get_trend_emoji function."""

    def test_hot_trend(self):
        """Test hot trend emoji."""
        assert _get_trend_emoji("hot") == "🔥"

    def test_cold_trend(self):
        """Test cold trend emoji."""
        assert _get_trend_emoji("cold") == "❄️"

    def test_stable_trend(self):
        """Test stable trend returns empty string."""
        assert _get_trend_emoji("stable") == ""


class TestGetRiskEmoji:
    """Tests for _get_risk_emoji function."""

    def test_out_risk(self):
        """Test OUT player emoji."""
        assert _get_risk_emoji(1.0) == "🚫"

    def test_high_risk(self):
        """Test high risk (doubtful) emoji."""
        assert _get_risk_emoji(0.75) == "⛔"
        assert _get_risk_emoji(0.5) == "⛔"

    def test_moderate_risk(self):
        """Test moderate risk (questionable) emoji."""
        assert _get_risk_emoji(0.4) == "⚠️"
        assert _get_risk_emoji(0.1) == "⚠️"

    def test_no_risk(self):
        """Test healthy player returns empty string."""
        assert _get_risk_emoji(0.0) == ""


class TestFormatCompactPick:
    """Tests for _format_compact_pick function."""

    @pytest.fixture
    def sample_rec(self):
        """Create a sample recommendation."""
        return PlayerRecommendation(
            name="Nikola Jokic",
            team="DEN",
            player_id=203999,
            opponent_team="LAL",
            avg_ttfl=55.0,
            weighted_avg=57.5,
            trend_factor=1.10,
            trend_direction="hot",
            consistency_factor=0.98,
            defense_factor=1.15,
            best_defender=None,
            defender_factor=1.0,
            adjusted_score=62.5,
            injury_status=None,
            dnp_risk=0.0,
            is_locked=False,
            games_played=10,
        )

    def test_compact_format_healthy(self, sample_rec):
        """Test compact format for healthy player."""
        result = _format_compact_pick(1, sample_rec)
        assert "Nikola Jokic" in result
        assert "DEN vs LAL" in result
        assert "62" in result or "63" in result  # Score rounded
        assert "🔥" in result  # Hot trend
        assert "🟢" in result  # Great matchup

    def test_compact_format_with_injury(self, sample_rec):
        """Test compact format with injury risk."""
        sample_rec.injury_status = "Questionable"
        sample_rec.dnp_risk = 0.4
        result = _format_compact_pick(1, sample_rec)
        assert "⚠️" in result


class TestFormatDetailedPick:
    """Tests for _format_detailed_pick function."""

    @pytest.fixture
    def sample_rec(self):
        """Create a sample recommendation."""
        return PlayerRecommendation(
            name="De'Aaron Fox",
            team="SAC",
            player_id=1628368,
            opponent_team="UTA",
            avg_ttfl=38.0,
            weighted_avg=40.5,
            trend_factor=1.08,
            trend_direction="hot",
            consistency_factor=0.92,
            defense_factor=1.12,
            best_defender=None,
            defender_factor=1.0,
            adjusted_score=42.3,
            injury_status=None,
            dnp_risk=0.0,
            is_locked=False,
            games_played=10,
        )

    def test_detailed_format_healthy(self, sample_rec):
        """Test detailed format for healthy player."""
        result = _format_detailed_pick(11, sample_rec)
        assert "De'Aaron Fox" in result
        assert "SAC vs UTA" in result
        assert "42.3" in result  # Score
        assert "38.0" in result  # Avg
        assert "🔥" in result  # Hot trend
        assert "Weak defense" in result  # Defense factor > 1.08
        assert "✅ Healthy" in result

    def test_detailed_format_with_injury(self, sample_rec):
        """Test detailed format with injury."""
        sample_rec.injury_status = "Questionable"
        sample_rec.dnp_risk = 0.4
        result = _format_detailed_pick(11, sample_rec)
        assert "Questionable" in result
        assert "40%" in result

    def test_detailed_format_with_defender(self, sample_rec):
        """Test detailed format with elite defender."""
        sample_rec.best_defender = "Rudy Gobert"
        sample_rec.defender_factor = 0.88
        sample_rec.defense_factor = 0.90  # Tough defense threshold
        result = _format_detailed_pick(11, sample_rec)
        assert "Rudy Gobert" in result
        assert "Tough defense" in result

    def test_detailed_format_cold_streak(self, sample_rec):
        """Test detailed format with cold streak."""
        sample_rec.trend_direction = "cold"
        sample_rec.trend_factor = 0.88
        result = _format_detailed_pick(11, sample_rec)
        assert "❄️" in result

    def test_detailed_format_stable(self, sample_rec):
        """Test detailed format with stable form."""
        sample_rec.trend_direction = "stable"
        result = _format_detailed_pick(11, sample_rec)
        assert "➡️ Stable" in result


class TestGenerateFullRankingsFile:
    """Tests for _generate_full_rankings_file function."""

    @pytest.fixture
    def sample_recommendations(self):
        """Create sample recommendations list."""
        recs = []
        for i in range(50):
            recs.append(PlayerRecommendation(
                name=f"Player {i+1}",
                team="TM1" if i % 2 == 0 else "TM2",
                player_id=1000 + i,
                opponent_team="OPP",
                avg_ttfl=50.0 - i * 0.5,
                weighted_avg=52.0 - i * 0.5,
                trend_factor=1.05 if i % 3 == 0 else (0.95 if i % 3 == 1 else 1.0),
                trend_direction="hot" if i % 3 == 0 else ("cold" if i % 3 == 1 else "stable"),
                consistency_factor=0.95,
                defense_factor=1.1 if i % 4 == 0 else 1.0,
                best_defender=None,
                defender_factor=1.0,
                adjusted_score=55.0 - i,
                injury_status="Questionable" if i == 5 else None,
                dnp_risk=0.4 if i == 5 else 0.0,
                is_locked=False,
                games_played=10,
            ))
        return recs

    def test_generates_header(self, sample_recommendations):
        """Test that file has proper header."""
        result = _generate_full_rankings_file(sample_recommendations, "2025-02-04")
        assert "TTFL Rankings - 2025-02-04" in result
        assert "Score" in result
        assert "Player" in result
        assert "Team" in result

    def test_contains_all_50_players(self, sample_recommendations):
        """Test that all 50 players are included."""
        result = _generate_full_rankings_file(sample_recommendations, "2025-02-04")
        assert "Player 1" in result
        assert "Player 50" in result

    def test_contains_legend(self, sample_recommendations):
        """Test that legend is included."""
        result = _generate_full_rankings_file(sample_recommendations, "2025-02-04")
        assert "Legend:" in result
        assert "[+] Great matchup" in result

    def test_shows_injury_status(self, sample_recommendations):
        """Test that injury status is shown."""
        result = _generate_full_rankings_file(sample_recommendations, "2025-02-04")
        assert "Questionable" in result
        assert "40%" in result

    def test_shows_trend(self, sample_recommendations):
        """Test that trend is shown."""
        result = _generate_full_rankings_file(sample_recommendations, "2025-02-04")
        assert "+5%" in result or "stable" in result
