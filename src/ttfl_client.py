"""Client to fetch pick history from TTFL website."""

import http.cookiejar
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


def load_cookies(cookie_file: str) -> dict[str, str]:
    """Load cookies from Netscape cookie file format."""
    cj = http.cookiejar.MozillaCookieJar(cookie_file)
    cj.load(ignore_discard=True, ignore_expires=True)

    cookies = {}
    for cookie in cj:
        cookies[cookie.name] = cookie.value
    return cookies


def get_pick_history(cookie_file: str) -> list[dict]:
    """
    Fetch pick history from TTFL website.

    Args:
        cookie_file: Path to Netscape-format cookie file

    Returns:
        List of picks: [{"date": "2025-01-21", "player": "Luka Dončić", "score": 69, "locked": True}, ...]
    """
    cookies = load_cookies(cookie_file)

    url = "https://fantasy.trashtalk.co/?tpl=historique"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    response = requests.get(url, cookies=cookies, headers=headers)
    response.raise_for_status()

    return parse_history_html(response.text)


def parse_history_html(html: str) -> list[dict]:
    """Parse the history page HTML to extract pick data."""
    soup = BeautifulSoup(html, "html.parser")

    picks = []

    # Find the history table
    # Columns: Date, Joueur, Pts, Reb, Ast, Stl, Blk, Ftm, Fgm, Fg3m, Malus, Score, [Bonus x2]
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            # TTFL uses mix of th and td elements
            cells = row.find_all(["td", "th"])
            # Need at least 12 columns (Date through Score)
            if len(cells) >= 12:
                pick = parse_history_row(cells)
                if pick:
                    picks.append(pick)

    return picks


def parse_history_row(cells) -> dict | None:
    """
    Parse a table row to extract pick information.

    Expected columns (0-indexed):
    0: Date (YYYY-MM-DD)
    1: Joueur (player name)
    2: Pts
    3: Reb
    4: Ast
    5: Stl
    6: Blk
    7: Ftm
    8: Fgm
    9: Fg3m
    10: Malus (turnovers + misses)
    11: Score (TTFL score)
    12: Bonus x2 / locked status (oui/non) - optional
    """
    try:
        date_text = cells[0].get_text(strip=True)
        player_name = cells[1].get_text(strip=True)
        score_text = cells[11].get_text(strip=True)

        # Validate date format (YYYY-MM-DD)
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            # Skip header rows or invalid dates
            return None

        # Parse score
        try:
            score = int(score_text)
        except ValueError:
            score = None

        # Check locked status (last column, if present)
        locked = False
        if len(cells) >= 13:
            lock_text = cells[12].get_text(strip=True).lower()
            locked = lock_text == "oui"

        # Extract stats for verification/debugging
        stats = {}
        try:
            stats = {
                "pts": int(cells[2].get_text(strip=True)),
                "reb": int(cells[3].get_text(strip=True)),
                "ast": int(cells[4].get_text(strip=True)),
                "stl": int(cells[5].get_text(strip=True)),
                "blk": int(cells[6].get_text(strip=True)),
                "ftm": int(cells[7].get_text(strip=True)),
                "fgm": int(cells[8].get_text(strip=True)),
                "fg3m": int(cells[9].get_text(strip=True)),
                "malus": int(cells[10].get_text(strip=True)),
            }
        except (ValueError, IndexError):
            pass

        return {
            "date": date_text,
            "player": player_name,
            "score": score,
            "locked": locked,
            "stats": stats,
        }
    except (IndexError, AttributeError):
        return None


def get_locked_players(cookie_file: str, lock_days: int = 30) -> set[str]:
    """
    Get set of player names that are currently locked.

    Args:
        cookie_file: Path to cookie file
        lock_days: Number of days a player stays locked (default 30)

    Returns:
        Set of locked player names
    """
    picks = get_pick_history(cookie_file)

    cutoff_date = datetime.now() - timedelta(days=lock_days)
    locked = set()

    for pick in picks:
        try:
            pick_date = datetime.strptime(pick["date"], "%Y-%m-%d")
            if pick_date >= cutoff_date:
                locked.add(pick["player"])
        except (ValueError, KeyError):
            # If we can't parse the date, check the locked flag
            if pick.get("locked"):
                locked.add(pick["player"])

    return locked
