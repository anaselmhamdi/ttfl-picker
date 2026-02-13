"""Discord webhook notifications with rich embeds."""

import os
from datetime import datetime

from discord_webhook import DiscordEmbed, DiscordWebhook

from .picker import PlayerRecommendation
from .session import InjuredPlayer


def _get_trend_emoji(direction: str) -> str:
    """Get trend emoji."""
    if direction == "hot":
        return "🔥"
    elif direction == "cold":
        return "❄️"
    return ""


def _get_risk_emoji(dnp_risk: float) -> str:
    """Get risk emoji."""
    if dnp_risk >= 1.0:
        return "🚫"
    elif dnp_risk >= 0.5:
        return "⛔"
    elif dnp_risk > 0:
        return "⚠️"
    return ""


def _get_matchup_emoji(defense_factor: float, defender_factor: float) -> str:
    """Get matchup quality emoji."""
    combined = defense_factor * defender_factor
    if combined >= 1.10:
        return "🟢"
    elif combined >= 1.0:
        return "🟡"
    elif combined >= 0.90:
        return "🟠"
    else:
        return "🔴"


def _format_detailed_pick(rank: int, rec: PlayerRecommendation) -> str:
    """Format a pick with detailed analysis."""
    matchup = _get_matchup_emoji(rec.defense_factor, rec.defender_factor)

    # Build matchup text based on combined factor (same as emoji logic)
    combined = rec.defense_factor * rec.defender_factor
    matchup_text = f"{matchup} "
    if combined >= 1.10:
        matchup_text += "Weak defense"
    elif combined >= 1.0:
        matchup_text += "Average defense"
    elif combined >= 0.90:
        matchup_text += "Tough defense"
    else:
        matchup_text += "Very tough defense"

    if rec.best_defender and rec.defender_factor < 0.95:
        matchup_text += f" (vs {rec.best_defender})"

    # Build status text (only show if injured)
    if rec.dnp_risk >= 1.0:
        status = "\n🚫 OUT"
    elif rec.dnp_risk >= 0.5:
        status = f"\n⛔ {rec.injury_status} ({int(rec.dnp_risk*100)}%)"
    elif rec.dnp_risk > 0:
        status = f"\n⚠️ {rec.injury_status} ({int(rec.dnp_risk*100)}%)"
    else:
        status = ""

    # Build trend text
    if rec.trend_direction == "hot":
        trend_text = f"🔥 {rec.trend_display}"
    elif rec.trend_direction == "cold":
        trend_text = f"❄️ {rec.trend_display}"
    else:
        trend_text = "➡️ Stable"

    return (
        f"**#{rank} {rec.name}** ({rec.team} vs {rec.opponent_team})\n"
        f"Score: **{rec.adjusted_score:.1f}** | Avg: {rec.avg_ttfl:.1f} | {trend_text}\n"
        f"{matchup_text}"
        f"{status}"
    )


def _build_picks_embed(
    recommendations: list[PlayerRecommendation],
    start_rank: int,
    end_rank: int,
    date: str,
    earliest_game_time: datetime | None = None,
) -> DiscordEmbed | None:
    """Build embed for a range of picks using detailed format.

    Args:
        recommendations: Full list of recommendations
        start_rank: Starting rank (1-indexed)
        end_rank: Ending rank (1-indexed, inclusive)
        date: Date string for the title
        earliest_game_time: Earliest game time in Paris timezone (for first embed only)

    Returns:
        DiscordEmbed or None if no picks in range
    """
    # Convert to 0-indexed slice
    picks = recommendations[start_rank - 1 : end_rank]

    if not picks:
        return None

    # Title varies based on range
    if start_rank == 1:
        title = f"🏀 TTFL {date} - Picks #{start_rank}-{start_rank + len(picks) - 1}"
    else:
        title = f"🏀 Picks #{start_rank}-{start_rank + len(picks) - 1}"

    # Color varies based on range
    colors = ["2ecc71", "3498db", "9b59b6", "e67e22", "e74c3c"]
    color_index = (start_rank - 1) // 10
    color = colors[color_index] if color_index < len(colors) else "95a5a6"

    # Add deadline description for first embed only
    description = None
    if start_rank == 1 and earliest_game_time:
        time_str = earliest_game_time.strftime("%Hh%M")
        description = f"⏰ Picks close at **{time_str}** (Paris time)"

    embed = DiscordEmbed(title=title, description=description, color=color)

    # Add each pick as a field
    for i, rec in enumerate(picks, start_rank):
        embed.add_embed_field(
            name="",
            value=_format_detailed_pick(i, rec),
            inline=False,
        )

    return embed


def _build_injuries_embed(
    injuries: list[InjuredPlayer],
    date: str,
) -> DiscordEmbed | None:
    """Build embed for notable injuries (OUT/Doubtful).

    Returns:
        DiscordEmbed or None if no notable injuries.
    """
    if not injuries:
        return None

    out_players = [p for p in injuries if p.dnp_risk >= 1.0]
    doubtful_players = [p for p in injuries if 0.75 <= p.dnp_risk < 1.0]

    embed = DiscordEmbed(
        title=f"\U0001f3e5 Notable Injuries - {date}",
        color="e74c3c",
    )

    if out_players:
        lines = [f"\U0001f6ab **{p.name}** ({p.team} vs {p.opponent_team})" for p in out_players]
        embed.add_embed_field(
            name=f"Out ({len(out_players)})",
            value="\n".join(lines),
            inline=False,
        )

    if doubtful_players:
        lines = [f"\u26a0\ufe0f **{p.name}** ({p.team} vs {p.opponent_team})" for p in doubtful_players]
        embed.add_embed_field(
            name=f"Doubtful ({len(doubtful_players)})",
            value="\n".join(lines),
            inline=False,
        )

    return embed


def post_to_discord(
    recommendations: list[PlayerRecommendation],
    date: str,
    webhook_url: str | None = None,
    earliest_game_time: datetime | None = None,
    notable_injuries: list[InjuredPlayer] | None = None,
) -> bool:
    """Post recommendations to Discord with multiple messages.

    Sends separate messages with 10 picks each (up to 50 total),
    followed by a notable injuries embed if available.

    Args:
        recommendations: List of player recommendations
        date: Date string (YYYY-MM-DD)
        webhook_url: Optional webhook URL (defaults to DISCORD_WEBHOOK_URL env var)
        earliest_game_time: Earliest game time in Paris timezone (shown in first embed)
        notable_injuries: Optional list of notable injured players (OUT/Doubtful)

    Returns:
        True if posting succeeded, False otherwise

    Raises:
        ValueError: If no webhook URL is configured
    """
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_TTFL")
    if not url:
        raise ValueError("DISCORD_WEBHOOK_URL or DISCORD_TTFL not set in .env")

    if not recommendations:
        return False

    # Send messages in batches of 10 picks
    ranges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50)]
    success = True

    for start, end in ranges:
        if start > len(recommendations):
            break

        # Pass earliest_game_time only for first embed
        game_time = earliest_game_time if start == 1 else None
        embed = _build_picks_embed(recommendations, start, end, date, game_time)
        if not embed:
            continue

        # Add timestamp to first message only
        if start == 1:
            embed.set_timestamp()

        webhook = DiscordWebhook(url=url, username="TTFL Picker", rate_limit_retry=True)
        webhook.add_embed(embed)

        response = webhook.execute()
        if response.status_code != 200:
            success = False

    # Send injuries embed as final message
    if notable_injuries:
        injuries_embed = _build_injuries_embed(notable_injuries, date)
        if injuries_embed:
            webhook = DiscordWebhook(url=url, username="TTFL Picker", rate_limit_retry=True)
            webhook.add_embed(injuries_embed)
            response = webhook.execute()
            if response.status_code != 200:
                success = False

    return success
