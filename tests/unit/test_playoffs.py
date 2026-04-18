"""Tests for playoff bracket data and scarcity scoring."""

import pytest

from src.playoffs import (
    PLAYOFF_TEAMS,
    american_to_prob,
    elimination_tier,
    expected_remaining_games,
    is_playoff_team,
    playoff_team_ids,
    scarcity_factor,
    tier_emoji,
)


class TestAmericanToProb:
    def test_negative_odds_favorite(self):
        assert american_to_prob(-110) == pytest.approx(0.524, abs=0.01)

    def test_even_odds(self):
        assert american_to_prob(+100) == 0.5

    def test_heavy_underdog(self):
        assert american_to_prob(+75000) == pytest.approx(0.00133, abs=0.001)


class TestExpectedRemainingGames:
    def test_favorite_plays_more_games(self):
        okc = expected_remaining_games("OKC")
        phx = expected_remaining_games("PHX")
        assert okc > phx

    def test_unknown_team_returns_zero(self):
        assert expected_remaining_games("GSW") == 0.0

    def test_all_teams_play_at_least_one_series(self):
        for tc in PLAYOFF_TEAMS:
            # min 1 series = 5.5 games, but long-shot tails make it slightly less
            # (we sum p^0 + p^1 + ...; p^0 = 1 guarantees at least 5.5)
            assert expected_remaining_games(tc) >= 5.0


class TestScarcityFactor:
    def test_favorite_has_low_scarcity(self):
        assert scarcity_factor("OKC") < 0.6

    def test_longshot_has_high_scarcity(self):
        assert scarcity_factor("PHX") > 1.3

    def test_booker_beats_sga_gap(self):
        # The whole reason for playoff mode: a Suns player should outrank an OKC star
        # unless the OKC star's raw form is ~4x higher.
        gap = scarcity_factor("PHX") / scarcity_factor("OKC")
        assert gap > 3.0

    def test_ingram_beats_jaylen_brown_gap(self):
        gap = scarcity_factor("TOR") / scarcity_factor("BOS")
        assert gap > 1.5

    def test_unknown_team_returns_zero(self):
        assert scarcity_factor("GSW") == 0.0

    def test_lal_beats_hou_despite_higher_seed(self):
        # LAL is seed #4 vs HOU seed #5 but series odds make HOU favored
        # (Luka + Reaves injured). Scarcity should reflect LAL > HOU.
        assert scarcity_factor("LAL") > scarcity_factor("HOU")

    def test_series_odds_shift_scarcity(self):
        # Expected games uses current-series odds directly for round 1,
        # so a team with a tight matchup gets less scarcity than a clear underdog.
        # ATL (+220) should have less scarcity than PHX (+1300).
        assert scarcity_factor("ATL") < scarcity_factor("PHX")


class TestTeamFilters:
    def test_is_playoff_team_true(self):
        assert is_playoff_team("OKC")
        assert is_playoff_team("PHX")

    def test_is_playoff_team_false(self):
        assert not is_playoff_team("GSW")
        assert not is_playoff_team("MEM")

    def test_playoff_team_ids_has_16_teams(self):
        ids = playoff_team_ids()
        assert len(ids) == 16
        assert all(isinstance(i, int) for i in ids)


class TestEliminationTier:
    def test_okc_is_favorite(self):
        assert elimination_tier("OKC") == "favorite"

    def test_phx_is_early_out(self):
        assert elimination_tier("PHX") == "early-out"

    def test_unknown_team(self):
        assert elimination_tier("GSW") == "unknown"

    def test_all_tiers_represented(self):
        tiers = {elimination_tier(t) for t in PLAYOFF_TEAMS}
        assert {"favorite", "contender", "longshot", "early-out"} <= tiers


class TestTierEmoji:
    def test_known_tiers(self):
        assert tier_emoji("favorite") == "🏆"
        assert tier_emoji("early-out") == "🪦"

    def test_unknown_tier_returns_empty(self):
        assert tier_emoji("foo") == ""
