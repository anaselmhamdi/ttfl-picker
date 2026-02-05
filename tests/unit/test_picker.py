"""Tests for picker functions."""

import pytest

from src.form_analysis import FormAnalysis
from src.picker import (
    PlayerRecommendation,
    calculate_final_score,
    format_recommendations,
)


class TestCalculateFinalScore:
    """Tests for calculate_final_score function."""

    def test_basic_calculation(self):
        """Test basic final score calculation."""
        form_analysis = FormAnalysis(
            weighted_avg=40.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=40.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.0,
            defender_factor=1.0,
            dnp_risk=0.0,
        )

        assert result == 40.0

    def test_with_hot_trend(self):
        """Test final score with hot trend factor."""
        form_analysis = FormAnalysis(
            weighted_avg=40.0,
            trend_factor=1.10,
            trend_direction="hot",
            consistency_factor=1.0,
            simple_avg=38.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.0,
            defender_factor=1.0,
            dnp_risk=0.0,
        )

        # 40.0 * 1.10 * 1.0 * 1.0 * 1.0 = 44.0
        assert result == 44.0

    def test_with_weak_defense(self):
        """Test final score against weak defense (bonus)."""
        form_analysis = FormAnalysis(
            weighted_avg=40.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=40.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.15,  # Weak defense = bonus
            defender_factor=1.0,
            dnp_risk=0.0,
        )

        # 40.0 * 1.0 * 1.0 * 1.15 * 1.0 = 46.0
        assert result == 46.0

    def test_with_elite_defender(self):
        """Test final score against elite defender (penalty)."""
        form_analysis = FormAnalysis(
            weighted_avg=40.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=40.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.0,
            defender_factor=0.85,  # Elite defender = penalty
            dnp_risk=0.0,
        )

        # 40.0 * 1.0 * 1.0 * 1.0 * 0.85 = 34.0
        assert result == 34.0

    def test_with_injury_risk(self):
        """Test final score with DNP risk."""
        form_analysis = FormAnalysis(
            weighted_avg=50.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=50.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.0,
            defender_factor=1.0,
            dnp_risk=0.40,  # 40% chance of DNP
        )

        # 50.0 * (1 - 0.40) = 30.0
        assert result == 30.0

    def test_full_combination(self):
        """Test final score with all factors combined."""
        form_analysis = FormAnalysis(
            weighted_avg=45.0,
            trend_factor=1.15,
            trend_direction="hot",
            consistency_factor=0.90,
            simple_avg=42.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.10,
            defender_factor=0.92,
            dnp_risk=0.10,
        )

        # form_score = 45.0 * 1.15 * 0.90 = 46.575
        # defense_adjusted = 46.575 * 1.10 = 51.2325
        # matchup_adjusted = 51.2325 * 0.92 = 47.13390
        # final = 47.13390 * (1 - 0.10) = 42.42051
        assert abs(result - 42.42) < 0.1

    def test_use_form_disabled(self):
        """Test final score with form analysis disabled."""
        form_analysis = FormAnalysis(
            weighted_avg=45.0,
            trend_factor=1.20,  # Would be applied if form enabled
            trend_direction="hot",
            consistency_factor=0.85,  # Would be applied if form enabled
            simple_avg=40.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.0,
            defender_factor=1.0,
            dnp_risk=0.0,
            use_form=False,
        )

        # Should use simple_avg (40.0) instead of form_score
        assert result == 40.0

    def test_use_defense_disabled(self):
        """Test final score with defense adjustments disabled."""
        form_analysis = FormAnalysis(
            weighted_avg=40.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=40.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.20,  # Would be applied if defense enabled
            defender_factor=0.80,  # Would be applied if defense enabled
            dnp_risk=0.0,
            use_defense=False,
        )

        # Should ignore defense_factor and defender_factor
        assert result == 40.0

    def test_out_player(self):
        """Test final score for player marked as OUT."""
        form_analysis = FormAnalysis(
            weighted_avg=50.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=50.0,
        )

        result = calculate_final_score(
            form_analysis=form_analysis,
            defense_factor=1.0,
            defender_factor=1.0,
            dnp_risk=1.0,  # 100% = OUT
        )

        # 50.0 * (1 - 1.0) = 0.0
        assert result == 0.0


class TestPlayerRecommendation:
    """Tests for PlayerRecommendation dataclass."""

    @pytest.fixture
    def sample_recommendation(self):
        """Create a sample recommendation."""
        return PlayerRecommendation(
            name="LeBron James",
            team="LAL",
            player_id=2544,
            opponent_team="GSW",
            avg_ttfl=45.5,
            weighted_avg=47.2,
            trend_factor=1.08,
            trend_direction="hot",
            consistency_factor=0.95,
            defense_factor=1.05,
            best_defender="Draymond Green",
            defender_factor=0.92,
            adjusted_score=42.3,
            injury_status="Questionable",
            dnp_risk=0.40,
            is_locked=False,
            games_played=10,
        )

    def test_status_display_locked(self, sample_recommendation):
        """Test status display for locked player."""
        sample_recommendation.is_locked = True
        assert sample_recommendation.status_display == "Locked"

    def test_status_display_healthy(self, sample_recommendation):
        """Test status display for healthy player."""
        sample_recommendation.injury_status = None
        sample_recommendation.is_locked = False
        assert sample_recommendation.status_display == "✓"

    def test_status_display_questionable(self, sample_recommendation):
        """Test status display for questionable player."""
        sample_recommendation.is_locked = False
        assert "Questionable" in sample_recommendation.status_display

    def test_is_out_true(self, sample_recommendation):
        """Test is_out property when player is OUT."""
        sample_recommendation.dnp_risk = 1.0
        assert sample_recommendation.is_out is True

    def test_is_out_false(self, sample_recommendation):
        """Test is_out property when player is available."""
        sample_recommendation.dnp_risk = 0.40
        assert sample_recommendation.is_out is False

    def test_trend_display_positive(self, sample_recommendation):
        """Test trend display for hot streak."""
        sample_recommendation.trend_factor = 1.15
        assert sample_recommendation.trend_display == "+15%"

    def test_trend_display_negative(self, sample_recommendation):
        """Test trend display for cold streak."""
        sample_recommendation.trend_factor = 0.88
        assert sample_recommendation.trend_display == "-12%"

    def test_trend_display_neutral(self, sample_recommendation):
        """Test trend display for stable performance."""
        sample_recommendation.trend_factor = 1.0
        assert sample_recommendation.trend_display == "0%"


class TestFormatRecommendations:
    """Tests for format_recommendations function."""

    @pytest.fixture
    def sample_recommendations(self):
        """Create sample recommendations list."""
        return [
            PlayerRecommendation(
                name="Nikola Jokic",
                team="DEN",
                player_id=203999,
                opponent_team="LAL",
                avg_ttfl=55.0,
                weighted_avg=57.5,
                trend_factor=1.05,
                trend_direction="hot",
                consistency_factor=0.98,
                defense_factor=1.10,
                best_defender=None,
                defender_factor=1.0,
                adjusted_score=62.5,
                injury_status=None,
                dnp_risk=0.0,
                is_locked=False,
                games_played=10,
            ),
            PlayerRecommendation(
                name="Luka Doncic",
                team="DAL",
                player_id=1629029,
                opponent_team="BOS",
                avg_ttfl=50.0,
                weighted_avg=48.5,
                trend_factor=0.95,
                trend_direction="cold",
                consistency_factor=0.92,
                defense_factor=0.95,
                best_defender="Jrue Holiday",
                defender_factor=0.88,
                adjusted_score=38.2,
                injury_status="Questionable",
                dnp_risk=0.40,
                is_locked=False,
                games_played=10,
            ),
        ]

    def test_basic_format(self, sample_recommendations):
        """Test basic formatting output."""
        result = format_recommendations(sample_recommendations, "2025-01-25")

        assert "TTFL Picks for 2025-01-25" in result
        assert "Nikola Jokic" in result
        assert "Luka Doncic" in result
        assert "DEN" in result
        assert "DAL" in result

    def test_verbose_format(self, sample_recommendations):
        """Test verbose formatting output."""
        result = format_recommendations(
            sample_recommendations, "2025-01-25", verbose=True
        )

        assert "detailed breakdown" in result
        assert "Form" in result
        assert "Trend" in result
        assert "Def" in result
        assert "Dfdr" in result

    def test_empty_recommendations(self):
        """Test formatting with empty list."""
        result = format_recommendations([], "2025-01-25")

        assert "TTFL Picks for 2025-01-25" in result

    def test_trend_indicators(self, sample_recommendations):
        """Test that trend indicators are shown."""
        result = format_recommendations(sample_recommendations, "2025-01-25")

        # Jokic is hot, Doncic is cold
        assert "^" in result or "v" in result

    def test_legend_included(self, sample_recommendations):
        """Test that legend is included."""
        result = format_recommendations(sample_recommendations, "2025-01-25")

        assert "Legend:" in result
        assert "Hot streak" in result or "hot" in result.lower()
