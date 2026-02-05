# TTFL Picker modules

from datetime import datetime


def get_current_season() -> str:
    """
    Get the current NBA season string (e.g., "2025-26").

    NBA seasons span two calendar years. The season starts in October
    and ends in June. Before October, we're in the previous season.
    """
    now = datetime.now()
    year = now.year
    month = now.month

    # NBA season starts in October
    # If we're in Oct-Dec, season is current_year to next_year
    # If we're in Jan-Sep, season is previous_year to current_year
    if month >= 10:
        start_year = year
    else:
        start_year = year - 1

    end_year = start_year + 1
    return f"{start_year}-{str(end_year)[-2:]}"
