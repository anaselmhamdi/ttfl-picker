"""Tests for form analysis functions."""

import pytest

from src.form_analysis import (
    GAME_WEIGHTS,
    FormAnalysis,
    analyze_form,
    calculate_consistency_factor,
    calculate_form_score,
    calculate_trend_factor,
    calculate_weighted_average,
)


class TestCalculateWeightedAverage:
    """Tests for calculate_weighted_average function."""

    def test_standard_scores(self, sample_ttfl_scores):
        """Test weighted average with 10 games."""
        result = calculate_weighted_average(sample_ttfl_scores)
        # Manual calculation:
        # scores = [45, 38, 42, 35, 50, 28, 44, 39, 41, 36]
        # weights = [0.25, 0.18, 0.14, 0.11, 0.09, 0.07, 0.06, 0.05, 0.03, 0.02]
        # weighted_sum = 45*0.25 + 38*0.18 + 42*0.14 + 35*0.11 + 50*0.09 +
        #                28*0.07 + 44*0.06 + 39*0.05 + 41*0.03 + 36*0.02
        # = 11.25 + 6.84 + 5.88 + 3.85 + 4.5 + 1.96 + 2.64 + 1.95 + 1.23 + 0.72 = 40.82
        assert 40.5 < result < 41.5

    def test_empty_scores(self):
        """Test weighted average with empty list."""
        result = calculate_weighted_average([])
        assert result == 0.0

    def test_single_score(self):
        """Test weighted average with single score."""
        result = calculate_weighted_average([50])
        # Single score with normalized weight should equal the score itself
        assert result == 50.0

    def test_two_scores(self):
        """Test weighted average with two scores."""
        result = calculate_weighted_average([60, 40])
        # Weights: [0.25, 0.18], normalized to sum=1
        # normalized: [0.25/0.43, 0.18/0.43] = [0.581, 0.419]
        # weighted: 60*0.581 + 40*0.419 = 34.88 + 16.74 = 51.63
        assert 51 < result < 52.5

    def test_recent_games_weighted_more(self, hot_streak_scores):
        """Test that recent games are weighted more heavily."""
        # hot_streak_scores = [55, 50, 45, 40, 35, 30, 28, 25, 22, 20]
        # Simple average = 35
        # Weighted average should be > 35 because recent games are higher
        simple_avg = sum(hot_streak_scores) / len(hot_streak_scores)
        weighted_avg = calculate_weighted_average(hot_streak_scores)
        assert weighted_avg > simple_avg

    def test_cold_streak_weighted_less(self, cold_streak_scores):
        """Test that cold streak reduces weighted average."""
        # cold_streak_scores = [20, 25, 30, 35, 40, 45, 48, 50, 52, 55]
        # Simple average = 40
        # Weighted average should be < 40 because recent games are lower
        simple_avg = sum(cold_streak_scores) / len(cold_streak_scores)
        weighted_avg = calculate_weighted_average(cold_streak_scores)
        assert weighted_avg < simple_avg


class TestCalculateTrendFactor:
    """Tests for calculate_trend_factor function."""

    def test_hot_streak(self, hot_streak_scores):
        """Test trend factor for hot streak (increasing scores)."""
        factor, direction = calculate_trend_factor(hot_streak_scores)
        assert factor > 1.0
        assert direction == "hot"

    def test_cold_streak(self, cold_streak_scores):
        """Test trend factor for cold streak (decreasing scores)."""
        factor, direction = calculate_trend_factor(cold_streak_scores)
        assert factor < 1.0
        assert direction == "cold"

    def test_stable_performance(self, consistent_scores):
        """Test trend factor for stable performance."""
        factor, direction = calculate_trend_factor(consistent_scores)
        assert 0.95 <= factor <= 1.05
        assert direction == "stable"

    def test_too_few_games(self):
        """Test trend factor with fewer than 3 games."""
        factor, direction = calculate_trend_factor([50, 45])
        assert factor == 1.0
        assert direction == "stable"

    def test_single_game(self):
        """Test trend factor with single game."""
        factor, direction = calculate_trend_factor([50])
        assert factor == 1.0
        assert direction == "stable"

    def test_empty_scores(self):
        """Test trend factor with empty list."""
        factor, direction = calculate_trend_factor([])
        assert factor == 1.0
        assert direction == "stable"

    def test_trend_factor_bounds(self, hot_streak_scores, cold_streak_scores):
        """Test that trend factor is bounded between 0.80 and 1.20."""
        hot_factor, _ = calculate_trend_factor(hot_streak_scores)
        cold_factor, _ = calculate_trend_factor(cold_streak_scores)

        assert 0.80 <= hot_factor <= 1.20
        assert 0.80 <= cold_factor <= 1.20

    def test_extreme_hot_streak(self):
        """Test that extreme trends are capped at max adjustment."""
        # Very steep increase
        extreme_scores = [100, 80, 60, 40, 20, 10, 5, 3, 2, 1]
        factor, direction = calculate_trend_factor(extreme_scores)
        assert factor <= 1.20
        assert direction == "hot"


class TestCalculateConsistencyFactor:
    """Tests for calculate_consistency_factor function."""

    def test_consistent_player(self, consistent_scores):
        """Test consistency factor for consistent player."""
        factor = calculate_consistency_factor(consistent_scores)
        # Low variance should result in factor close to 1.0
        assert factor >= 0.95

    def test_inconsistent_player(self, inconsistent_scores):
        """Test consistency factor for inconsistent player."""
        factor = calculate_consistency_factor(inconsistent_scores)
        # High variance should result in penalty
        assert factor < 0.95

    def test_consistency_bounds(self, inconsistent_scores):
        """Test that consistency factor is bounded between 0.85 and 1.00."""
        factor = calculate_consistency_factor(inconsistent_scores)
        assert 0.85 <= factor <= 1.00

    def test_too_few_games(self):
        """Test consistency factor with fewer than 3 games."""
        factor = calculate_consistency_factor([50, 45])
        assert factor == 1.0

    def test_single_game(self):
        """Test consistency factor with single game."""
        factor = calculate_consistency_factor([50])
        assert factor == 1.0

    def test_empty_scores(self):
        """Test consistency factor with empty list."""
        factor = calculate_consistency_factor([])
        assert factor == 1.0

    def test_identical_scores(self):
        """Test consistency factor with identical scores (zero variance)."""
        factor = calculate_consistency_factor([40, 40, 40, 40, 40])
        assert factor == 1.0

    def test_all_zeros(self):
        """Test consistency factor with all zeros."""
        factor = calculate_consistency_factor([0, 0, 0, 0, 0])
        # Mean is 0, should return 1.0 to avoid division by zero
        assert factor == 1.0


class TestAnalyzeForm:
    """Tests for analyze_form function."""

    def test_standard_analysis(self, sample_ttfl_scores):
        """Test full form analysis."""
        result = analyze_form(sample_ttfl_scores)

        assert isinstance(result, FormAnalysis)
        assert result.weighted_avg > 0
        assert result.simple_avg == sum(sample_ttfl_scores) / len(sample_ttfl_scores)
        assert 0.80 <= result.trend_factor <= 1.20
        assert result.trend_direction in ["hot", "cold", "stable"]
        assert 0.85 <= result.consistency_factor <= 1.00

    def test_empty_scores(self):
        """Test form analysis with empty scores."""
        result = analyze_form([])

        assert result.weighted_avg == 0.0
        assert result.simple_avg == 0.0
        assert result.trend_factor == 1.0
        assert result.trend_direction == "stable"
        assert result.consistency_factor == 1.0

    def test_hot_streak_analysis(self, hot_streak_scores):
        """Test form analysis for hot streak."""
        result = analyze_form(hot_streak_scores)

        assert result.trend_direction == "hot"
        assert result.trend_factor > 1.0

    def test_cold_streak_analysis(self, cold_streak_scores):
        """Test form analysis for cold streak."""
        result = analyze_form(cold_streak_scores)

        assert result.trend_direction == "cold"
        assert result.trend_factor < 1.0


class TestCalculateFormScore:
    """Tests for calculate_form_score function."""

    def test_form_score_calculation(self):
        """Test form score calculation formula."""
        analysis = FormAnalysis(
            weighted_avg=40.0,
            trend_factor=1.10,
            trend_direction="hot",
            consistency_factor=0.95,
            simple_avg=38.0,
        )

        result = calculate_form_score(analysis)
        # Expected: 40.0 * 1.10 * 0.95 = 41.8
        assert abs(result - 41.8) < 0.01

    def test_form_score_with_penalty(self):
        """Test form score with cold streak and inconsistency penalties."""
        analysis = FormAnalysis(
            weighted_avg=50.0,
            trend_factor=0.90,
            trend_direction="cold",
            consistency_factor=0.85,
            simple_avg=52.0,
        )

        result = calculate_form_score(analysis)
        # Expected: 50.0 * 0.90 * 0.85 = 38.25
        assert abs(result - 38.25) < 0.01

    def test_form_score_neutral(self):
        """Test form score with neutral factors."""
        analysis = FormAnalysis(
            weighted_avg=45.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=45.0,
        )

        result = calculate_form_score(analysis)
        assert result == 45.0
