#!/usr/bin/env python3
"""Main entry point for Bratislava Betting Syndicate."""

import argparse
import os
from typing import Optional, List
import uuid
from datetime import datetime

from data.odds_api import OddsAPIClient
from data.scrapers import NikeScraper
from data.odds_aggregator import OddsAggregator
from data.daily_odds_fetcher import DailyOddsFetcher
from simulation.graph import run_simulation
from config.settings import settings
from monitoring.agent_monitor import AgentMonitor
from database.schema import init_db, SessionLocal, User, Simulation
from database.auth import auth_manager, UserTier
from monitoring.logger import logger
from notification.email_sender import EmailSender
from notification.discord_notifier import DiscordNotifier
import asyncio


def main(
    num_games: int = 100,
    sport: str = "soccer_epl",
    use_sample_data: bool = True,
    use_aggregator: bool = False,
    use_daily_fetcher: bool = False,
    show_live: bool = True,
    filter_sports: Optional[List[str]] = None,
    filter_leagues: Optional[List[str]] = None,
    max_per_sport: Optional[int] = None
):
    """Run the Bratislava Betting Syndicate simulation.

    Args:
        num_games: Number of games to simulate
        sport: Sport to bet on
        use_sample_data: Use sample data instead of API calls
        use_aggregator: Use multi-source odds aggregator
        use_daily_fetcher: Use daily fetcher for today's top leagues
        show_live: Show live agent thinking and decisions
        filter_sports: Only analyze these sports
        filter_leagues: Only analyze these leagues
        max_per_sport: Maximum games per sport
    """
    # Initialize monitor
    monitor = AgentMonitor() if show_live else None
    
    # Initialize Discord notifier
    discord_notifier = DiscordNotifier()
    
    if monitor:
        monitor.show_header()
    else:
        print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   🎰 BRATISLAVA BETTING SYNDICATE 🎰                     ║
    ║   Multi-Agent AI Betting Simulation                       ║
    ║   Powered by LangGraph + Claude Sonnet 4.5                ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    if discord_notifier.enabled:
        print("📢 Discord notifications enabled")
        asyncio.run(discord_notifier.on_simulation_start(num_games, sport))

    # Validate settings
    try:
        settings.validate()
    except ValueError as e:
        if monitor:
            monitor.show_error(f"Configuration error: {e}")
            monitor.show_warning("Please set ANTHROPIC_API_KEY in your .env file")
        else:
            print(f"❌ Configuration error: {e}")
            print("Please set ANTHROPIC_API_KEY in your .env file")
        return

    # Initialize Database
    init_db()
    db = SessionLocal()
    
    # Ensure default user for CLI
    cli_email = os.getenv("CLI_USER_EMAIL", "cli_user@bratislava.local")
    user = db.query(User).filter(User.email == cli_email).first()
    if not user:
        user = auth_manager.create_user(
            db=db,
            email=cli_email,
            password="cli_password_insecure_but_local",
            tier=UserTier.ENTERPRISE # Unlimited for CLI
        )
        if not monitor:
            print(f"✅ Created default CLI user: {cli_email}")

    # Fetch odds data
    if monitor:
        monitor.log_event("INFO", "Fetching odds data...")
    else:
        print("📡 Fetching odds data...")
    
    games = []
    
    if use_daily_fetcher:
        # Use daily fetcher for today's available games (all sports from Nike.sk)
        fetcher = DailyOddsFetcher(
            use_nike=True,
            use_odds_api=True,
            filter_sports=filter_sports,
            filter_leagues=filter_leagues,
            max_per_sport=max_per_sport
        )
        games_by_sport = fetcher.get_todays_games(hours_ahead=24)
        # Flatten all games into one list
        for sport_games in games_by_sport.values():
            games.extend(sport_games)
        
        # Update sport to reflect multi-sport
        sport = "multi-sport"
        
        if monitor:
            monitor.log_event("INFO", f"Using daily fetcher: {len(games)} today's games")
        else:
            print(f"   Using daily fetcher: {len(games)} today's games")
    
    elif use_aggregator:
        # Use multi-source aggregator
        aggregator = OddsAggregator()
        games = aggregator.get_all_odds(sport='soccer')
    
    else:
        # Use single source (OddsAPI)
        odds_client = OddsAPIClient()

        if use_sample_data:
            if monitor:
                monitor.log_event("INFO", "Using sample data (no API calls)")
            else:
                print("   Using sample data (no API calls)")
            games = odds_client.get_sample_games()
            sport = "demo"  # Set sport to demo for sample data
        else:
            if monitor:
                monitor.log_event("INFO", f"Fetching live odds for {sport}")
            else:
                print(f"   Fetching live odds for {sport}")
            games = odds_client.get_odds(sport=sport)

            if not games:
                if monitor:
                    monitor.show_warning("No games found, using sample data")
                else:
                    print("   No games found, using sample data")
                games = odds_client.get_sample_games()

    if monitor:
        monitor.show_success(f"Found {len(games)} games")
        monitor.show_separator()
    else:
        print(f"   Found {len(games)} games\n")

    # Create Simulation Record
    simulation_id = str(uuid.uuid4())
    simulation = Simulation(
        id=simulation_id,
        user_id=user.id,
        num_games=num_games,
        starting_bankroll=settings.STARTING_BANKROLL,
        kelly_fraction=settings.KELLY_FRACTION,
        sport=sport,
        use_live_data=not use_sample_data,
        status="in_progress",
        created_at=datetime.utcnow()
    )
    db.add(simulation)
    db.commit()

    if monitor:
        monitor.log_event("INFO", f"Simulation started: {simulation_id}")

    # Run simulation
    results = run_simulation(
        games=games,
        num_games=num_games,
        starting_bankroll=settings.STARTING_BANKROLL,
        monitor=monitor,  # Pass monitor to simulation
        db=db,
        user_id=user.id,
        simulation_id=simulation_id,
        sport=sport,
        use_live_data=not use_sample_data,
        notifier=discord_notifier  # Pass Discord notifier
    )

    # Save user email before closing DB
    user_email = user.email

    # Close DB
    db.close()

    # Print top performing agents
    if monitor:
        monitor.show_separator()
    
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

    # Notify Discord of completion
    if discord_notifier.enabled:
        asyncio.run(discord_notifier.on_simulation_complete(
            num_games=num_games,
            total_wagered=results.get("total_wagered", 0)
        ))
    
    # Send email report if configured
    email_sender = EmailSender()
    if email_sender.enabled:
        print("📧 Sending email report...")
        email_sent = email_sender.send_simulation_report(
            recipient_email=user_email,
            simulation_id=simulation_id,
            sport=sport,
            num_games=num_games,
            predictions=results.get("results", []),
            total_wagered=results.get("total_wagered", 0)
        )
        if email_sent:
            print(f"✅ Email sent to {user_email}\n")
        else:
            print("❌ Failed to send email\n")
    
    print("💡 TIP: Run 'streamlit run gui/streamlit_app.py' for interactive GUI")
    print("📊 TIP: Check export/ folder for PDF reports")
    print("📧 TIP: Configure email with: export SENDER_EMAIL='...' SENDER_PASSWORD='...'\n")


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
        "--sample",
        action="store_true",
        help="Use sample data instead of live API"
    )
    parser.add_argument(
        "--aggregator",
        action="store_true",
        help="Use multi-source odds aggregator"
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Use daily fetcher for today's top leagues (overrides other options)"
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="Disable live agent monitoring (classic mode)"
    )
    parser.add_argument(
        "--sports",
        type=str,
        default=None,
        help="Comma-separated sports to analyze (e.g., 'soccer,basketball,hockey')"
    )
    parser.add_argument(
        "--leagues",
        type=str,
        default=None,
        help="Comma-separated leagues to analyze (e.g., 'premier_league,la_liga,nba')"
    )
    parser.add_argument(
        "--max-per-sport",
        type=int,
        default=None,
        help="Maximum games per sport (e.g., 5)"
    )
    parser.add_argument(
        "--show-leagues",
        action="store_true",
        help="Show available leagues and exit"
    )
    parser.add_argument(
        "--update-results",
        action="store_true",
        help="Update pending bets with real match results (experimental)"
    )
    parser.add_argument(
        "--leaderboard",
        action="store_true",
        help="Show agent leaderboard"
    )

    args = parser.parse_args()
    
    # Handle --show-leagues
    if args.show_leagues:
        import sys
        from data.daily_odds_fetcher import DailyOddsFetcher
        fetcher = DailyOddsFetcher(use_nike=True, use_odds_api=False)
        print("\n📊 AVAILABLE LEAGUES BY SPORT\n" + "=" * 70)
        leagues = fetcher.get_available_leagues()
        for sport, league_set in sorted(leagues.items()):
            print(f"\n{sport.upper()}:")
            for league in sorted(league_set):
                print(f"  • {league}")
        print("\n" + "=" * 70)
        sys.exit(0)
    
    # Handle --leaderboard
    if args.leaderboard:
        import sys
        from database.results_updater import ResultsUpdater
        db_url = os.getenv("DATABASE_URL", "sqlite:///bratislava.db")
        updater = ResultsUpdater(db_url)
        updater.print_leaderboard(days=7)
        sys.exit(0)
    
    # Handle --update-results
    if args.update_results:
        import sys
        print("\n⚠️  EXPERIMENTAL: Results matching system\n")
        print("Note: This requires real match scores from an external source.")
        print("Currently, this is a placeholder implementation.")
        print("To use this feature, you would need to:")
        print("  1. Fetch real scores from Flashscore/ESPN/OddsAPI")
        print("  2. Match them with your placed bets")
        print("  3. Settle bets and calculate P&L")
        print("\nThis functionality is being developed.")
        print("\nFor now, use --leaderboard to see agent performance")
        sys.exit(0)

    main(
        num_games=args.games,
        sport=args.sport,
        use_sample_data=args.sample,
        use_aggregator=args.aggregator,
        use_daily_fetcher=args.daily,
        show_live=not args.no_live,
        filter_sports=args.sports.split(',') if args.sports else None,
        filter_leagues=args.leagues.split(',') if args.leagues else None,
        max_per_sport=args.max_per_sport
    )
