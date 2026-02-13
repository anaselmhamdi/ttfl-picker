#!/usr/bin/env python3
"""TTFL Picker CLI - Get daily TTFL pick recommendations."""

import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv

from src.discord_notify import post_to_discord
from src.nba_data import get_earliest_game_time
from src.picker import format_recommendations
from src.session import TTFLSession, format_plan


@click.command()
@click.option("--date", "-d", default=None, help="Date (YYYY-MM-DD, default: today)")
@click.option("--top", "-n", default=10, help="Number of recommendations (default: 10)")
@click.option("--show-risky", is_flag=True, help="Include players marked OUT")
@click.option("--show-locked", is_flag=True, help="Include locked players in output")
@click.option("--ignore-locks", is_flag=True, help="Skip personal locks (no cookies needed)")
@click.option("--cookies", "-c", default="fantasy.trashtalk.co_cookies.txt", help="Cookie file path")
@click.option("--output", "-o", default=None, help="Save results to file")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed scoring breakdown")
@click.option("--no-defense", is_flag=True, help="Disable defense adjustments")
@click.option("--no-form", is_flag=True, help="Use simple average instead of form analysis")
@click.option("--discord", is_flag=True, help="Post results to Discord webhook (requires .env)")
@click.option("--plan", "-p", default=0, help="Plan picks for next N days (e.g., --plan 7)")
def main(date, top, show_risky, show_locked, ignore_locks, cookies, output, verbose, no_defense, no_form, discord, plan):
    """Get daily TTFL pick recommendations."""
    cookie_path = Path(cookies)

    # Check cookie file exists (skip if --ignore-locks)
    if not ignore_locks and not cookie_path.exists():
        click.echo(f"Error: Cookie file not found: {cookies}", err=True)
        click.echo("Use --ignore-locks to skip personal lock check.", err=True)
        sys.exit(1)

    # Determine display date
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            click.echo(f"Error: Invalid date format '{date}'. Use YYYY-MM-DD.", err=True)
            sys.exit(1)
        display_date = date
    else:
        display_date = datetime.now().strftime("%Y-%m-%d")

    try:
        # Create session (fetches all shared data once)
        session = TTFLSession(
            cookie_file=str(cookie_path),
            ignore_locks=ignore_locks,
            verbose=True,
        )

        # Multi-day planning mode
        if plan > 0:
            click.echo(f"\n🗓️  Planning optimal picks for the next {plan} days...\n")

            plans = session.plan_picks(days=plan)
            output_text = format_plan(plans)

            click.echo()
            click.echo(output_text)

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(output_text)
                click.echo(f"\nPlan saved to: {output}")

            return

        # Single-day recommendations mode
        click.echo(f"\nFetching recommendations for {display_date}...")

        recommendations = session.get_recommendations(
            date=date,
            top_n=top,
            include_risky=show_risky,
            include_locked=show_locked,
            use_form=not no_form,
            use_defense=not no_defense,
        )

        if not recommendations:
            click.echo(f"\nNo recommendations available for {display_date}.")
            click.echo("This could mean:")
            click.echo("  - No NBA games scheduled for this date")
            click.echo("  - Could not fetch player data")
            sys.exit(0)

        output_text = format_recommendations(recommendations, display_date, verbose=verbose)
        click.echo()
        click.echo(output_text)

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_text)
            click.echo(f"\nResults saved to: {output}")

        # Post to Discord if requested
        if discord:
            load_dotenv()
            try:
                # Get earliest game time for deadline display
                _, games = session.get_players_for_date(date)
                earliest_game_time = get_earliest_game_time(games)

                # Get notable injuries for the digest
                notable_injuries = session.get_notable_injuries(date)

                success = post_to_discord(
                    recommendations,
                    display_date,
                    earliest_game_time=earliest_game_time,
                    notable_injuries=notable_injuries,
                )
                if success:
                    click.echo("\nPosted to Discord successfully!")
                else:
                    click.echo("\nFailed to post to Discord.", err=True)
            except ValueError as e:
                click.echo(f"\nDiscord error: {e}", err=True)
                sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\nAborted.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
