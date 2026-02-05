"""Form analysis: weighted averages, trends, and consistency factors."""

import statistics
from dataclasses import dataclass


# Weights for last 10 games (most recent first)
GAME_WEIGHTS = [0.25, 0.18, 0.14, 0.11, 0.09, 0.07, 0.06, 0.05, 0.03, 0.02]

# Maximum adjustments
MAX_TREND_ADJUSTMENT = 0.20  # +/- 20%
MAX_CONSISTENCY_PENALTY = 0.15  # -15% max


@dataclass
class FormAnalysis:
    """Result of form analysis for a player."""

    weighted_avg: float
    trend_factor: float  # 0.80 to 1.20
    trend_direction: str  # "hot", "cold", "stable"
    consistency_factor: float  # 0.85 to 1.00
    simple_avg: float


def calculate_weighted_average(scores: list[float]) -> float:
    """
    Calculate weighted average where recent games count more.

    Args:
        scores: List of TTFL scores, most recent first

    Returns:
        Weighted average score
    """
    if not scores:
        return 0.0

    # Use available weights up to the number of games
    num_games = min(len(scores), len(GAME_WEIGHTS))
    weights = GAME_WEIGHTS[:num_games]

    # Normalize weights to sum to 1
    weight_sum = sum(weights)
    normalized_weights = [w / weight_sum for w in weights]

    # Calculate weighted average
    weighted_sum = sum(score * weight for score, weight in zip(scores[:num_games], normalized_weights))

    return weighted_sum


def calculate_trend_factor(scores: list[float]) -> tuple[float, str]:
    """
    Calculate trend factor using linear regression slope.

    Args:
        scores: List of TTFL scores, most recent first

    Returns:
        Tuple of (trend_factor, trend_direction)
        - trend_factor: 0.80 to 1.20 multiplier
        - trend_direction: "hot", "cold", or "stable"
    """
    if len(scores) < 3:
        return 1.0, "stable"

    # Reverse to chronological order (oldest first) for regression
    chronological = list(reversed(scores))
    n = len(chronological)

    # Simple linear regression
    x_mean = (n - 1) / 2
    y_mean = sum(chronological) / n

    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(chronological))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 1.0, "stable"

    slope = numerator / denominator

    # Convert slope to percentage change per game relative to average
    if y_mean == 0:
        return 1.0, "stable"

    slope_pct = slope / y_mean

    # Scale: +1% per game slope -> +10% trend factor (over ~10 games)
    # Cap at MAX_TREND_ADJUSTMENT
    raw_adjustment = slope_pct * n
    capped_adjustment = max(-MAX_TREND_ADJUSTMENT, min(MAX_TREND_ADJUSTMENT, raw_adjustment))

    trend_factor = 1.0 + capped_adjustment

    # Determine direction
    if capped_adjustment > 0.05:
        direction = "hot"
    elif capped_adjustment < -0.05:
        direction = "cold"
    else:
        direction = "stable"

    return trend_factor, direction


def calculate_consistency_factor(scores: list[float]) -> float:
    """
    Calculate consistency factor based on variance.

    Lower variance = higher consistency = bonus (no bonus, just no penalty)
    Higher variance = lower consistency = penalty up to MAX_CONSISTENCY_PENALTY

    Args:
        scores: List of TTFL scores

    Returns:
        Consistency factor (0.85 to 1.00)
    """
    if len(scores) < 3:
        return 1.0

    mean = sum(scores) / len(scores)
    if mean == 0:
        return 1.0

    # Calculate coefficient of variation (std dev / mean)
    try:
        std_dev = statistics.stdev(scores)
    except statistics.StatisticsError:
        return 1.0

    cv = std_dev / mean

    # High CV = inconsistent player
    # CV of 0.3 (~30% variation) = moderate penalty
    # CV of 0.5+ = maximum penalty

    # Map CV to penalty: 0.0-0.2 = no penalty, 0.5+ = max penalty
    if cv <= 0.2:
        return 1.0

    penalty_range = min(1.0, (cv - 0.2) / 0.3)  # 0 to 1 scale
    penalty = penalty_range * MAX_CONSISTENCY_PENALTY

    return 1.0 - penalty


def analyze_form(scores: list[float]) -> FormAnalysis:
    """
    Perform complete form analysis for a player.

    Args:
        scores: List of TTFL scores, most recent first

    Returns:
        FormAnalysis with all computed factors
    """
    if not scores:
        return FormAnalysis(
            weighted_avg=0.0,
            trend_factor=1.0,
            trend_direction="stable",
            consistency_factor=1.0,
            simple_avg=0.0,
        )

    simple_avg = sum(scores) / len(scores)
    weighted_avg = calculate_weighted_average(scores)
    trend_factor, trend_direction = calculate_trend_factor(scores)
    consistency_factor = calculate_consistency_factor(scores)

    return FormAnalysis(
        weighted_avg=weighted_avg,
        trend_factor=trend_factor,
        trend_direction=trend_direction,
        consistency_factor=consistency_factor,
        simple_avg=simple_avg,
    )


def calculate_form_score(analysis: FormAnalysis) -> float:
    """
    Calculate the final form-adjusted score.

    Args:
        analysis: FormAnalysis object

    Returns:
        Form-adjusted score
    """
    return analysis.weighted_avg * analysis.trend_factor * analysis.consistency_factor
