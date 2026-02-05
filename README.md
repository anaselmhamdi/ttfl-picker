# TTFL Picker

A local CLI tool that recommends daily TTFL (TrashTalk Fantasy League) picks based on expected performance.

## Setup

```bash
# Install dependencies
uv sync

# Export your TTFL cookies from browser to: fantasy.trashtalk.co_cookies.txt
# (Use a browser extension like "Cookie-Editor" to export in Netscape format)
```

## Usage

```bash
# Get recommendations for today
uv run python main.py

# Specific date
uv run python main.py --date 2025-02-05

# Show top N recommendations
uv run python main.py --top 5

# Save results to file
uv run python main.py -o results/2025-02-04.txt

# Include players marked OUT (excluded by default)
uv run python main.py --show-risky

# Include locked players (for reference)
uv run python main.py --show-locked
```

## How It Works

1. Fetches your pick history from TTFL website (via cookies)
2. Identifies players locked in the last 30 days
3. Fetches tonight's NBA games and player rosters
4. Fetches injury reports from ESPN/CBS Sports
5. Calculates average TTFL score from last 10 games
6. Applies risk adjustment based on injury status
7. Ranks and displays top recommendations

## TTFL Score Formula

```
POSITIVE: PTS + REB + AST + STL + BLK + FGM + 3PM + FTM
NEGATIVE: TO + FG_MISS + 3P_MISS + FT_MISS

TTFL = POSITIVE - NEGATIVE
```

## DNP Risk Adjustments

- **OUT**: Excluded (100% DNP risk)
- **Doubtful**: Score × 0.25 (75% DNP risk)
- **Questionable**: Score × 0.60 (40% DNP risk)
- **Probable**: Score × 0.90 (10% DNP risk)

## Files

```
ttfl-picker/
├── main.py                         # CLI entry point
├── fantasy.trashtalk.co_cookies.txt  # Your TTFL cookies (gitignored)
├── results/                        # Saved recommendations (optional)
└── src/
    ├── ttfl.py                     # TTFL score calculation
    ├── ttfl_client.py              # TTFL website client
    ├── nba_data.py                 # NBA API data fetching
    ├── injuries.py                 # Injury report fetching
    └── picker.py                   # Main recommendation logic
```
