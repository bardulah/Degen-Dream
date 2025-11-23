#!/usr/bin/env python3
"""Main entry point for Bratislava Betting Syndicate."""

import argparse
from typing import Optional

from data.odds_api import OddsAPIClient
from data.scrapers import NikeScraper
from simulation.graph import run_simulation
from config.settings import settings


def main(
    num_games: int = 100,
    sport: str = "soccer_epl",
    use_sample_data: bool = True
):
    """Run the Bratislava Betting Syndicate simulation.

    Args:
        num_games: Number of games to simulate
        sport: Sport to bet on
        use_sample_data: Use sample data instead of API calls
    """
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   🎰 BRATISLAVA BETTING SYNDICATE 🎰                     ║
    ║   Multi-Agent AI Betting Simulation                       ║
    ║   Powered by LangGraph + Claude Sonnet 4.5                ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Validate settings
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please set ANTHROPIC_API_KEY in your .env file")
        return

    # Fetch odds data
    print("📡 Fetching odds data...")
    odds_client = OddsAPIClient()

    if use_sample_data:
        print("   Using sample data (no API calls)")
        games = odds_client.get_sample_games()
    else:
        print(f"   Fetching live odds for {sport}")
        games = odds_client.get_odds(sport=sport)

        if not games:
            print("   No games found, using sample data")
            games = odds_client.get_sample_games()

    print(f"   Found {len(games)} games\n")

    # Run simulation
    results = run_simulation(
        games=games,
        num_games=num_games,
        starting_bankroll=settings.STARTING_BANKROLL
    )

    # Print top performing agents
    print("\n" + "=" * 70)
    print("🏆 AGENT PERFORMANCE RANKINGS")
    print("=" * 70)

    agent_stats = sorted(
        results["agent_stats"],
        key=lambda x: x["roi"],
        reverse=True
    )

    for i, agent in enumerate(agent_stats, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{emoji} {i}. {agent['name']} ({agent['type']})")
        print(f"      ROI: {agent['roi']:+.2f}% | Bankroll: €{agent['bankroll']:.2f}")
        print(f"      Win Rate: {agent['win_rate']:.1f}% | Bets: {agent['total_bets']}")
        print()

    print("\n💡 TIP: Run 'streamlit run gui/streamlit_app.py' for interactive GUI")
    print("📊 TIP: Check export/ folder for PDF reports\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bratislava Betting Syndicate - Multi-Agent Betting Sim"
    )
    parser.add_argument(
        "--games",
        type=int,
        default=100,
        help="Number of games to simulate (default: 100)"
    )
    parser.add_argument(
        "--sport",
        type=str,
        default="soccer_epl",
        help="Sport to bet on (default: soccer_epl)"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live API data instead of sample data"
    )

    args = parser.parse_args()

    main(
        num_games=args.games,
        sport=args.sport,
        use_sample_data=not args.live
    )
