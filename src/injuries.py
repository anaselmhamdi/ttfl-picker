"""Fetch injury reports and assess DNP risk."""

import requests
from bs4 import BeautifulSoup


# DNP risk probabilities by injury status
DNP_RISK = {
    "out": 1.0,
    "doubtful": 0.75,
    "questionable": 0.40,
    "probable": 0.10,
    "available": 0.0,
    "day-to-day": 0.30,
    "gtd": 0.30,  # Game-time decision
}


def get_dnp_risk(status: str | None) -> float:
    """
    Convert injury status to DNP probability.

    Args:
        status: Injury status string (e.g., "Out", "Questionable")

    Returns:
        Probability of DNP (0.0 to 1.0)
    """
    if status is None:
        return 0.0

    status_lower = status.lower().strip()

    # Check for exact matches
    if status_lower in DNP_RISK:
        return DNP_RISK[status_lower]

    # Check for partial matches
    for key, risk in DNP_RISK.items():
        if key in status_lower:
            return risk

    return 0.0


def get_injury_status_display(status: str | None) -> str:
    """Get display string for injury status."""
    if status is None:
        return "✓"

    status_lower = status.lower().strip()
    risk = get_dnp_risk(status)

    if risk >= 1.0:
        return "🚫 Out"
    elif risk >= 0.5:
        return f"⚠️ {status.title()}"
    elif risk > 0:
        return f"⚠️ {status.title()}"
    else:
        return "✓"


def fetch_espn_injuries() -> dict[str, str]:
    """
    Fetch injury report from ESPN.

    Returns:
        Dict mapping player name to injury status
    """
    url = "https://www.espn.com/nba/injuries"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return parse_espn_injuries(response.text)
    except Exception as e:
        print(f"Warning: Could not fetch ESPN injuries: {e}")
        return {}


def parse_espn_injuries(html: str) -> dict[str, str]:
    """Parse ESPN injury page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    injuries = {}

    # ESPN uses tables for injury data
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                # First cell usually has player name, second has status
                player_cell = cells[0]
                status_cell = cells[1] if len(cells) > 1 else None

                player_name = player_cell.get_text(strip=True)
                status = status_cell.get_text(strip=True) if status_cell else None

                if player_name and status:
                    # Clean up player name (remove position, etc.)
                    # ESPN format: "Player Name POS"
                    parts = player_name.rsplit(" ", 1)
                    if len(parts) > 1 and len(parts[-1]) <= 3:
                        player_name = parts[0]

                    injuries[player_name] = status

    return injuries


def fetch_cbssports_injuries() -> dict[str, str]:
    """
    Fetch injury report from CBS Sports.

    Returns:
        Dict mapping player name to injury status
    """
    url = "https://www.cbssports.com/nba/injuries/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return parse_cbssports_injuries(response.text)
    except Exception as e:
        print(f"Warning: Could not fetch CBS Sports injuries: {e}")
        return {}


def parse_cbssports_injuries(html: str) -> dict[str, str]:
    """Parse CBS Sports injury page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    injuries = {}

    # CBS Sports uses tables with specific classes
    injury_rows = soup.find_all("tr", class_=lambda x: x and "TableBase" in str(x) if x else False)

    for row in injury_rows:
        cells = row.find_all("td")
        if len(cells) >= 3:
            player_cell = cells[0]
            status_cell = cells[2]  # Status is usually in 3rd column

            player_link = player_cell.find("a")
            player_name = player_link.get_text(strip=True) if player_link else player_cell.get_text(strip=True)
            status = status_cell.get_text(strip=True)

            if player_name and status:
                injuries[player_name] = status

    return injuries


def get_injury_report() -> dict[str, str]:
    """
    Fetch combined injury report from multiple sources.

    Returns:
        Dict mapping player name to injury status
    """
    injuries = {}

    # Try ESPN first
    espn_injuries = fetch_espn_injuries()
    injuries.update(espn_injuries)

    # CBS Sports as backup/supplement
    cbs_injuries = fetch_cbssports_injuries()

    # Merge CBS injuries (don't overwrite ESPN data)
    for player, status in cbs_injuries.items():
        if player not in injuries:
            injuries[player] = status

    return injuries


def normalize_player_name(name: str) -> str:
    """Normalize player name for matching."""
    # Remove accents and special characters for matching
    import unicodedata
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    return name.lower().strip()


def match_player_injury(player_name: str, injuries: dict[str, str]) -> str | None:
    """
    Find injury status for a player, handling name variations.

    Args:
        player_name: Player name to look up
        injuries: Dict of injury statuses

    Returns:
        Injury status or None if not found
    """
    # Exact match
    if player_name in injuries:
        return injuries[player_name]

    # Normalized match
    normalized = normalize_player_name(player_name)

    for inj_player, status in injuries.items():
        if normalize_player_name(inj_player) == normalized:
            return status

    # Partial match (for names like "LeBron James" vs "James, LeBron")
    player_parts = set(normalized.split())
    for inj_player, status in injuries.items():
        inj_parts = set(normalize_player_name(inj_player).split())
        # If most parts match, consider it a match
        if len(player_parts & inj_parts) >= min(2, len(player_parts)):
            return status

    return None
