#!/usr/bin/env python3
"""Daily scheduler for Bratislava Betting Syndicate."""

import schedule
import time
import logging
from datetime import datetime
from main import main

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_daily_simulation():
    """Run the daily simulation."""
    logger.info("=" * 70)
    logger.info("🎰 STARTING DAILY SIMULATION")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 70)
    
    try:
        # Run with Nike scraper for real data
        main(
            num_games=100,
            sport="soccer",
            use_sample_data=False,  # Use real data from Nike
            use_aggregator=True,    # Use multi-source aggregator
            show_live=True          # Show live monitoring
        )
        logger.info("✅ Daily simulation completed successfully")
    except Exception as e:
        logger.error(f"❌ Daily simulation failed: {e}", exc_info=True)
    
    logger.info("=" * 70 + "\n")


def schedule_daily_run(hour: int = 8, minute: int = 0):
    """Schedule the simulation to run daily at specified time.
    
    Args:
        hour: Hour to run (0-23, in UTC)
        minute: Minute to run (0-59)
    """
    time_str = f"{hour:02d}:{minute:02d}"
    schedule.every().day.at(time_str).do(run_daily_simulation)
    
    logger.info(f"📅 Scheduled daily run at {time_str} UTC")
    logger.info("Press Ctrl+C to stop")
    
    # Keep scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Daily scheduler for Bratislava Betting Syndicate"
    )
    parser.add_argument(
        "--time",
        type=str,
        default="08:00",
        help="Time to run daily in HH:MM format (UTC, default: 08:00)"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run simulation immediately (don't schedule)"
    )
    
    args = parser.parse_args()
    
    if args.run_now:
        # Run immediately
        run_daily_simulation()
    else:
        # Schedule for later
        try:
            hour, minute = map(int, args.time.split(":"))
            schedule_daily_run(hour, minute)
        except (ValueError, IndexError):
            logger.error("Invalid time format. Use HH:MM (e.g., 08:00)")
            exit(1)
