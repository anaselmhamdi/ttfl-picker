# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TTFL Picker is a local CLI tool for the TrashTalk Fantasy League (French NBA fantasy game). It recommends daily player picks based on expected TTFL performance, accounting for locked players and injury risks.

## Commands

```bash
# Install dependencies
uv sync

# Run the picker (today's recommendations)
uv run python main.py

# Run without personal locks (for bots/general use)
uv run python main.py --ignore-locks

# Run with options
uv run python main.py --date 2025-02-05 --top 5 -o results/output.txt

# Post to Discord (requires .env with DISCORD_WEBHOOK_URL)
uv run python main.py --ignore-locks --discord

# Plan picks for the next N days (simulates locks)
uv run python main.py --plan 7 --ignore-locks
```

## Architecture

**Data Flow:**
1. `ttfl_client.py` → Fetches pick history from fantasy.trashtalk.co (via cookies), identifies 30-day locked players
2. `nba_data.py` → Fetches tonight's games and player rosters via `nba_api`, calculates average TTFL from last 10 games
3. `injuries.py` → Scrapes ESPN/CBS Sports for injury reports, maps status to DNP risk percentages
4. `picker.py` → Combines all data, applies risk-adjusted scoring (`adjusted = avg_ttfl × (1 - dnp_risk)`), ranks recommendations
5. `main.py` → CLI interface

**Key Business Logic:**
- TTFL Score: `(PTS + REB + AST + STL + BLK + FGM + 3PM + FTM) - (TO + FG_MISS + 3P_MISS + FT_MISS)`
- Players are locked for 30 days after being picked
- DNP (Did Not Play) = 0 points but lock still applies (worst outcome)
- Risk adjustments: OUT=excluded, Doubtful=75% penalty, Questionable=40%, Probable=10%

## Cookie Setup

Export TTFL cookies from browser to `fantasy.trashtalk.co_cookies.txt` in Netscape format. This file is gitignored.

## Discord Integration

1. Create a webhook in your Discord server (Server Settings → Integrations → Webhooks)
2. Copy the webhook URL
3. Create `.env` file: `DISCORD_WEBHOOK_URL=your_webhook_url`
4. Run with `--discord` flag

## Testing

```bash
# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_ttfl.py -v

# Run only fast unit tests
uv run pytest tests/unit/ -v

# Run integration tests
uv run pytest tests/integration/ -v
```
