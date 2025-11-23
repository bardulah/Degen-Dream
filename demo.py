#!/usr/bin/env python3
"""Quick demo script to test Bratislava Betting Syndicate."""

from data.odds_api import OddsAPIClient
from simulation.graph import SyndicateGraph
from agents.base_agent import Game
from export.pdf_generator import generate_roi_report, generate_quick_summary
from config.settings import settings
import os


def demo():
    """Run a quick demo of the system."""

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   🎰 BRATISLAVA BETTING SYNDICATE - DEMO 🎰              ║
    ║   Quick demo of multi-agent betting simulation            ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Check if API key is set
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set")
        print("   This demo will work with sample data, but Claude agents won't respond")
        print("   Set your API key in .env to see full agent debates\n")

    # Get sample games
    print("📡 Loading sample games...")
    client = OddsAPIClient()
    games = client.get_sample_games()
    print(f"   Loaded {len(games)} sample games\n")

    # Create syndicate
    print("🤖 Initializing 10-agent syndicate...")
    syndicate = SyndicateGraph()

    print("\n👥 Meet the agents:")
    for agent in syndicate.agents:
        print(f"   • {agent.name} ({agent.agent_type.value})")

    print("\n" + "=" * 70)
    print("Starting 3-game demo simulation...")
    print("=" * 70)

    # Run on 3 games
    for i, game in enumerate(games[:3], 1):
        print(f"\n{'='*70}")
        print(f"GAME {i}/3")
        print(f"{'='*70}")

        market_context = {
            "public_betting": {"home": 65, "away": 35},
            "line_movements": "Stable",
            "pinnacle_odds": "Not available in demo",
            "nike_data": {
                "public_percentage": 65,
                "sharp_action": "Unknown"
            }
        }

        bet = syndicate.analyze_game(game, market_context)

        if bet:
            # Simulate outcome
            import random
            won = random.random() < 0.52  # Slight edge
            profit_loss = syndicate.bankroll_manager.settle_bet(bet, won)

            print(f"\n{'✅ WON' if won else '❌ LOST'}: {profit_loss:+.2f} EUR")
        else:
            print("\n⚠️  No consensus bet placed")

        syndicate.bankroll_manager.take_snapshot()

    # Final stats
    print("\n" + "=" * 70)
    print("DEMO RESULTS")
    print("=" * 70)

    stats = syndicate.bankroll_manager.get_statistics()
    print(f"\n💰 Final Bankroll: €{stats['current_bankroll']:.2f}")
    print(f"📈 ROI: {stats['roi']:+.2f}%")
    print(f"🎯 Win Rate: {stats['win_rate']:.1f}%")
    print(f"🎲 Total Bets: {stats['total_bets']}")

    print("\n🏆 Top 3 Agents:")
    agent_stats = sorted(syndicate.get_agent_stats(), key=lambda x: x['roi'], reverse=True)
    for i, agent in enumerate(agent_stats[:3], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        print(f"{emoji} {i}. {agent['name']}: {agent['roi']:+.2f}% ROI")

    # Generate PDF if we have results
    if stats['total_bets'] > 0:
        print("\n📄 Generating PDF report...")
        results = {
            'stats': stats,
            'agent_stats': agent_stats,
            'results': [],
            'performance': syndicate.bankroll_manager.get_performance_over_time()
        }

        try:
            pdf_path = generate_roi_report(results, "demo_report.pdf")
            print(f"   PDF saved to: {pdf_path}")
        except Exception as e:
            print(f"   PDF generation failed: {e}")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)

    print("\n📚 Next steps:")
    print("   1. Run full simulation: python main.py --games 100")
    print("   2. Launch GUI: streamlit run gui/streamlit_app.py")
    print("   3. Read docs: SETUP.md and MONETIZATION.md")
    print("   4. Set ANTHROPIC_API_KEY in .env for full agent debates")

    print("\n💡 Tip: The real magic happens when you run 100+ games and watch")
    print("   the sharps vs degens battle play out over time!\n")


if __name__ == "__main__":
    demo()
