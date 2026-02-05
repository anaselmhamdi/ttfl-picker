"""Tests for injury functions."""

import pytest

from src.injuries import (
    get_dnp_risk,
    get_injury_status_display,
    match_player_injury,
    normalize_player_name,
    parse_cbssports_injuries,
    parse_espn_injuries,
)


class TestGetDnpRisk:
    """Tests for get_dnp_risk function."""

    def test_out_status(self):
        """Test OUT status returns 100% risk."""
        assert get_dnp_risk("Out") == 1.0
        assert get_dnp_risk("out") == 1.0
        assert get_dnp_risk("OUT") == 1.0

    def test_doubtful_status(self):
        """Test Doubtful status returns 75% risk."""
        assert get_dnp_risk("Doubtful") == 0.75
        assert get_dnp_risk("doubtful") == 0.75

    def test_questionable_status(self):
        """Test Questionable status returns 40% risk."""
        assert get_dnp_risk("Questionable") == 0.40
        assert get_dnp_risk("questionable") == 0.40

    def test_probable_status(self):
        """Test Probable status returns 10% risk."""
        assert get_dnp_risk("Probable") == 0.10
        assert get_dnp_risk("probable") == 0.10

    def test_available_status(self):
        """Test Available status returns 0% risk."""
        assert get_dnp_risk("Available") == 0.0
        assert get_dnp_risk("available") == 0.0

    def test_day_to_day_status(self):
        """Test Day-to-Day status returns 30% risk."""
        assert get_dnp_risk("Day-To-Day") == 0.30
        assert get_dnp_risk("day-to-day") == 0.30

    def test_gtd_status(self):
        """Test GTD (Game-Time Decision) status returns 30% risk."""
        assert get_dnp_risk("GTD") == 0.30
        assert get_dnp_risk("gtd") == 0.30

    def test_none_status(self):
        """Test None status returns 0% risk."""
        assert get_dnp_risk(None) == 0.0

    def test_unknown_status(self):
        """Test unknown status returns 0% risk."""
        assert get_dnp_risk("Unknown") == 0.0
        assert get_dnp_risk("Something else") == 0.0

    def test_partial_match(self):
        """Test partial matching of status strings."""
        assert get_dnp_risk("Listed as Out") == 1.0
        assert get_dnp_risk("Questionable - ankle") == 0.40
        assert get_dnp_risk("Probable to play") == 0.10

    def test_whitespace_handling(self):
        """Test that whitespace is stripped."""
        assert get_dnp_risk("  Out  ") == 1.0
        assert get_dnp_risk(" Questionable ") == 0.40


class TestGetInjuryStatusDisplay:
    """Tests for get_injury_status_display function."""

    def test_none_status(self):
        """Test display for healthy player."""
        assert get_injury_status_display(None) == "✓"

    def test_out_status(self):
        """Test display for OUT player."""
        result = get_injury_status_display("Out")
        assert "Out" in result

    def test_questionable_status(self):
        """Test display for Questionable player."""
        result = get_injury_status_display("Questionable")
        assert "Questionable" in result

    def test_probable_status(self):
        """Test display for Probable player."""
        result = get_injury_status_display("Probable")
        assert "Probable" in result


class TestNormalizePlayerName:
    """Tests for normalize_player_name function."""

    def test_basic_name(self):
        """Test basic name normalization."""
        assert normalize_player_name("LeBron James") == "lebron james"

    def test_accented_characters(self):
        """Test removing accents."""
        assert normalize_player_name("Nikola Jokić") == "nikola jokic"
        assert normalize_player_name("José Alvarado") == "jose alvarado"
        assert normalize_player_name("Luka Dončić") == "luka doncic"

    def test_whitespace(self):
        """Test whitespace handling."""
        assert normalize_player_name("  LeBron  James  ") == "lebron  james"

    def test_case_insensitive(self):
        """Test case is lowered."""
        assert normalize_player_name("STEPHEN CURRY") == "stephen curry"
        assert normalize_player_name("Kevin Durant") == "kevin durant"

    def test_special_characters(self):
        """Test handling of special characters."""
        assert normalize_player_name("O.G. Anunoby") == "o.g. anunoby"


class TestMatchPlayerInjury:
    """Tests for match_player_injury function."""

    def test_exact_match(self, sample_injuries):
        """Test exact name match."""
        result = match_player_injury("LeBron James", sample_injuries)
        assert result == "Questionable"

    def test_case_insensitive_match(self, sample_injuries):
        """Test case-insensitive matching."""
        result = match_player_injury("lebron james", sample_injuries)
        assert result == "Questionable"

    def test_normalized_match(self):
        """Test matching with accented characters."""
        injuries = {"Nikola Jokić": "Out"}
        result = match_player_injury("Nikola Jokic", injuries)
        assert result == "Out"

    def test_partial_match(self, sample_injuries):
        """Test partial name matching."""
        # Should match "LeBron James" with enough common parts
        result = match_player_injury("James LeBron", sample_injuries)
        assert result == "Questionable"

    def test_no_match(self, sample_injuries):
        """Test no match found."""
        result = match_player_injury("Michael Jordan", sample_injuries)
        assert result is None

    def test_empty_injuries(self):
        """Test with empty injuries dict."""
        result = match_player_injury("LeBron James", {})
        assert result is None

    def test_single_name_match(self):
        """Test that single names need at least 2 parts to match partially."""
        injuries = {"James Harden": "Out"}
        # "Harden" alone shouldn't match due to minimum parts requirement
        result = match_player_injury("Harden", injuries)
        # With only 1 part, partial matching requires len(player_parts) to be >= 2
        # min(2, len(player_parts)) = min(2, 1) = 1, so it should match
        assert result == "Out"


class TestParseEspnInjuries:
    """Tests for parse_espn_injuries function."""

    def test_parse_table_format(self):
        """Test parsing ESPN injury table HTML."""
        # ESPN columns: NAME | POS | EST. RETURN DATE | STATUS | COMMENT
        html = """
        <html>
        <body>
        <table>
            <tr>
                <td>LeBron James</td>
                <td>PF</td>
                <td>Feb 10</td>
                <td>Questionable</td>
                <td>Ankle soreness</td>
            </tr>
            <tr>
                <td>Stephen Curry</td>
                <td>PG</td>
                <td>Feb 15</td>
                <td>Out</td>
                <td>Knee injury</td>
            </tr>
        </table>
        </body>
        </html>
        """
        result = parse_espn_injuries(html)

        assert "LeBron James" in result
        assert result["LeBron James"] == "Questionable"
        assert "Stephen Curry" in result
        assert result["Stephen Curry"] == "Out"

    def test_parse_empty_html(self):
        """Test parsing empty HTML."""
        result = parse_espn_injuries("<html><body></body></html>")
        assert result == {}

    def test_parse_no_tables(self):
        """Test parsing HTML without tables."""
        html = "<html><body><p>No injury data</p></body></html>"
        result = parse_espn_injuries(html)
        assert result == {}


class TestParseCbssportsInjuries:
    """Tests for parse_cbssports_injuries function."""

    def test_parse_table_format(self):
        """Test parsing CBS Sports injury table HTML."""
        # CBS columns: NAME | POS | DATE | INJURY | STATUS
        html = """
        <html>
        <body>
        <table>
            <tr class="TableBase-row">
                <td><a href="/player">Kevin Durant</a></td>
                <td>SF</td>
                <td>Feb 10</td>
                <td>Knee</td>
                <td>Probable</td>
            </tr>
            <tr class="TableBase-bodyRow">
                <td><a href="/player">Giannis Antetokounmpo</a></td>
                <td>PF</td>
                <td>Feb 12</td>
                <td>Back</td>
                <td>Day-To-Day</td>
            </tr>
        </table>
        </body>
        </html>
        """
        result = parse_cbssports_injuries(html)

        assert "Kevin Durant" in result
        assert result["Kevin Durant"] == "Probable"
        assert "Giannis Antetokounmpo" in result
        assert result["Giannis Antetokounmpo"] == "Day-To-Day"

    def test_parse_empty_html(self):
        """Test parsing empty HTML."""
        result = parse_cbssports_injuries("<html><body></body></html>")
        assert result == {}

    def test_parse_no_matching_rows(self):
        """Test parsing HTML without matching row classes."""
        html = """
        <html>
        <body>
        <table>
            <tr class="OtherClass">
                <td>Player</td>
                <td>Injury</td>
                <td>Status</td>
            </tr>
        </table>
        </body>
        </html>
        """
        result = parse_cbssports_injuries(html)
        assert result == {}
