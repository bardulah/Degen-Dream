#!/usr/bin/env python3
"""
Automated Result Updater - Runs on schedule to fetch results and send notifications.

This script:
1. Runs daily to check for finished games
2. Updates bet results automatically
3. Sends Discord/Telegram notifications
4. Can be run as a background service or cron job

Usage:
    python auto_updater.py              # Run once
    python auto_updater.py --daemon     # Run as background service
    python auto_updater.py --test       # Test mode (dry run)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import schedule
import time
import argparse
from datetime import datetime, timedelta
from typing import Dict, List

from data.result_matcher import ResultMatcher
from database.schema import SessionLocal, Simulation, Bet
from monitoring.logger import logger


class AutoUpdater:
    """Automatically fetch results and send notifications on schedule."""

    def __init__(self, enable_notifications: bool = True):
        """
        Initialize auto updater.

        Args:
            enable_notifications: Whether to send notifications
        """
        self.enable_notifications = enable_notifications
        self.last_run = None

    def check_and_update_results(self, days_back: int = 1):
        """
        Check for results from recent days.

        Args:
            days_back: How many days back to check (default: 1 = yesterday)

        Returns:
            Dictionary with update statistics
        """
        logger.info("=" * 70)
        logger.info("AUTOMATED RESULT UPDATE")
        logger.info("=" * 70)

        total_stats = {
            'dates_checked': 0,
            'total_checked': 0,
            'updated': 0,
            'won': 0,
            'lost': 0,
            'push': 0,
            'errors': 0
        }

        matcher = ResultMatcher()

        # Check last N days
        for i in range(days_back):
            check_date = datetime.now() - timedelta(days=i+1)
            date_str = check_date.strftime('%Y%m%d')

            logger.info(f"\nChecking {date_str}...")

            stats = matcher.fetch_and_update_results(date_str)

            # Aggregate stats
            total_stats['dates_checked'] += 1
            for key in ['total_checked', 'updated', 'won', 'lost', 'push', 'errors']:
                total_stats[key] += stats.get(key, 0)

            if stats['updated'] > 0:
                logger.info(f"✅ Updated {stats['updated']} bets for {date_str}")
            else:
                logger.info(f"No updates for {date_str}")

        logger.info("\n" + "=" * 70)
        logger.info("UPDATE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Dates Checked: {total_stats['dates_checked']}")
        logger.info(f"Bets Checked:  {total_stats['total_checked']}")
        logger.info(f"Bets Updated:  {total_stats['updated']}")
        logger.info(f"✅ Won:        {total_stats['won']}")
        logger.info(f"❌ Lost:       {total_stats['lost']}")
        logger.info(f"⚪ Push:       {total_stats['push']}")
        logger.info("=" * 70)

        self.last_run = datetime.now()

        # Send notifications if enabled
        if self.enable_notifications and total_stats['updated'] > 0:
            self._send_notifications(total_stats)

        return total_stats

    def _send_notifications(self, stats: Dict):
        """Send notifications about results."""
        try:
            # Try Discord first
            from scheduler.notifier import DiscordNotifier
            notifier = DiscordNotifier()
            if notifier.enabled:
                notifier.send_result_update(stats)
                logger.info("📢 Discord notification sent")
        except ImportError:
            logger.warning("Discord notifier not available")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

        try:
            # Try Telegram
            from scheduler.notifier import TelegramNotifier
            notifier = TelegramNotifier()
            if notifier.enabled:
                notifier.send_result_update(stats)
                logger.info("📢 Telegram notification sent")
        except ImportError:
            logger.warning("Telegram notifier not available")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

    def update_affected_simulations(self):
        """Update statistics for all affected simulations."""
        db = SessionLocal()
        try:
            # Find simulations awaiting results
            simulations = db.query(Simulation).filter(
                Simulation.status.in_(['in_progress', 'awaiting_results'])
            ).all()

            logger.info(f"\nUpdating {len(simulations)} simulations...")

            matcher = ResultMatcher(db)

            for sim in simulations:
                try:
                    sim_stats = matcher.update_simulation_stats(sim.id)
                    matcher.update_agent_stats(sim.id)

                    logger.info(
                        f"Updated {sim.id[:8]}: "
                        f"{sim_stats['settled_bets']}/{sim_stats['total_bets']} settled, "
                        f"ROI: {sim_stats['roi']:+.2f}%"
                    )
                except Exception as e:
                    logger.error(f"Failed to update simulation {sim.id[:8]}: {e}")

        finally:
            db.close()

    def run_daily_job(self):
        """Run the daily update job."""
        logger.info(f"\n{'='*70}")
        logger.info(f"DAILY JOB STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*70}\n")

        # Check yesterday's results
        stats = self.check_and_update_results(days_back=1)

        # Update all affected simulations
        if stats['updated'] > 0:
            self.update_affected_simulations()

        logger.info(f"\n{'='*70}")
        logger.info(f"DAILY JOB COMPLETED")
        logger.info(f"{'='*70}\n")

    def start_scheduler(self, run_time: str = "09:00"):
        """
        Start the scheduler as a daemon.

        Args:
            run_time: Time to run daily (HH:MM format)
        """
        logger.info(f"🤖 Starting Auto Updater Scheduler")
        logger.info(f"⏰ Scheduled to run daily at {run_time}")
        logger.info(f"📢 Notifications: {'Enabled' if self.enable_notifications else 'Disabled'}")
        logger.info(f"\nPress Ctrl+C to stop\n")

        # Schedule the job
        schedule.every().day.at(run_time).do(self.run_daily_job)

        # Also run immediately on startup
        logger.info("Running initial check...")
        self.run_daily_job()

        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("\n\n🛑 Scheduler stopped by user")


def main():
    parser = argparse.ArgumentParser(
        description="Automated result updater with scheduling"
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help="Run as background daemon (scheduled)"
    )
    parser.add_argument(
        '--time',
        type=str,
        default="09:00",
        help="Time to run daily (HH:MM format, default: 09:00)"
    )
    parser.add_argument(
        '--no-notifications',
        action='store_true',
        help="Disable notifications"
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help="Test mode (dry run)"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help="Number of days back to check (default: 1)"
    )

    args = parser.parse_args()

    updater = AutoUpdater(enable_notifications=not args.no_notifications)

    if args.daemon:
        # Run as scheduled daemon
        updater.start_scheduler(run_time=args.time)
    elif args.test:
        # Test mode - just check but don't update
        logger.info("🧪 TEST MODE - Checking results (no updates)\n")
        stats = updater.check_and_update_results(days_back=args.days)
        logger.info(f"\nTest completed. Would have updated {stats['updated']} bets.")
    else:
        # Run once
        updater.run_daily_job()


if __name__ == '__main__':
    main()
