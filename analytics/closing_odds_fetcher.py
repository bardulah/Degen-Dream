"""
Closing Odds Fetcher

This module handles the complex task of fetching closing odds:
1. Monitors upcoming games and their start times
2. Schedules odds fetching 10 minutes before each game
3. Stores the "closing line" (last odds before game starts)
4. Updates bets with CLV data

Two Implementation Approaches:
- Approach 1: Scheduled pre-game fetching (lighter, good enough)
- Approach 2: Continuous polling with history (more accurate, more complex)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import schedule
import uuid
from sqlalchemy.orm import Session

from database.schema import SessionLocal, Bet, OddsHistory
from data.odds_api_client import OddsAPIClient
from sports_score_fetcher import SportsScoreFetcher
from analytics.clv_tracker import CLVTracker
from monitoring.logger import logger


class ClosingOddsFetcher:
    """
    Fetches closing odds for upcoming games.

    Strategy:
    1. Every hour, check for games starting in next 2 hours
    2. Schedule odds fetch 10 minutes before each game
    3. Store as "closing odds"
    4. Update all bets for that game with CLV
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize closing odds fetcher.

        Args:
            db: Database session (optional)
        """
        self.espn = SportsScoreFetcher()
        self.odds_client = OddsAPIClient()  # Your existing odds fetcher
        self.clv_tracker = CLVTracker(db)
        self.db = db
        self._should_close_db = False

        if not self.db:
            self.db = SessionLocal()
            self._should_close_db = True

        # Track scheduled jobs to avoid duplicates
        self.scheduled_games = set()

    def __del__(self):
        """Clean up database connection."""
        if self._should_close_db and self.db:
            self.db.close()

    def get_upcoming_games(self, hours_ahead: int = 2) -> List[Dict]:
        """
        Get games starting in the next N hours.

        Args:
            hours_ahead: How many hours ahead to look

        Returns:
            List of upcoming games with start times
        """
        upcoming = []
        now = datetime.now()

        # Check today and tomorrow
        for days_offset in [0, 1]:
            check_date = now + timedelta(days=days_offset)
            date_str = check_date.strftime('%Y%m%d')

            # Fetch NBA games (expand for other sports)
            nba_url = f"{self.espn.BASE_URL}/basketball/nba/scoreboard"
            try:
                response = self.espn.session.get(nba_url, params={'dates': date_str}, timeout=10)
                data = response.json()

                for event in data.get('events', []):
                    # Parse start time
                    game_time_str = event.get('date')  # ISO 8601 format
                    if not game_time_str:
                        continue

                    game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))

                    # Check if game is upcoming
                    time_until_game = (game_time - now).total_seconds() / 3600  # hours

                    if 0 < time_until_game <= hours_ahead:
                        competition = event['competitions'][0]
                        competitors = competition['competitors']

                        home = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                        away = next((c for c in competitors if c.get('homeAway') == 'away'), None)

                        if home and away:
                            upcoming.append({
                                'game_id': event['id'],
                                'sport': 'nba',
                                'home_team': home['team']['displayName'],
                                'away_team': away['team']['displayName'],
                                'start_time': game_time,
                                'minutes_until_start': time_until_game * 60
                            })

            except Exception as e:
                logger.error(f"Error fetching upcoming games: {e}")

        return upcoming

    def fetch_and_store_closing_odds(self, game_id: str, sport: str, home_team: str, away_team: str):
        """
        Fetch current odds for a game and store as closing odds.

        This should be called ~10 minutes before game starts.

        Args:
            game_id: ESPN game ID
            sport: Sport type
            home_team: Home team name
            away_team: Away team name
        """
        logger.info(f"Fetching closing odds for {home_team} vs {away_team}")

        # Fetch current odds from your odds API
        try:
            # Example using your existing odds client
            odds_data = self.odds_client.fetch_live_odds(sport=sport)

            # Find this game in odds data
            closing_odds = None
            for game in odds_data:
                if (game.get('home_team') == home_team and
                    game.get('away_team') == away_team):
                    closing_odds = {
                        'home_odds': game.get('home_odds'),
                        'away_odds': game.get('away_odds'),
                        'fetched_at': datetime.now()
                    }
                    break

            if not closing_odds:
                logger.warning(f"Could not find closing odds for {home_team} vs {away_team}")
                return

            # Update all bets for this game
            self._update_bets_with_closing_odds(game_id, closing_odds)

            logger.info(
                f"✅ Stored closing odds: {home_team} {closing_odds['home_odds']} / "
                f"{away_team} {closing_odds['away_odds']}"
            )

        except Exception as e:
            logger.error(f"Error fetching closing odds: {e}")

    def _update_bets_with_closing_odds(self, game_id: str, closing_odds: Dict):
        """
        Update all bets for a game with closing odds and calculate CLV.

        Args:
            game_id: ESPN game ID
            closing_odds: Dict with home_odds, away_odds
        """
        # Find all bets for this game
        bets = self.db.query(Bet).filter(Bet.game_id_espn == game_id).all()

        for bet in bets:
            # Determine which closing odds to use based on bet team
            if bet.bet_team in closing_odds:
                closing_line = closing_odds[bet.bet_team]
            else:
                # Try to match team name
                # (You may need fuzzy matching here)
                continue

            # Update bet with closing odds and CLV
            self.clv_tracker.update_bet_clv(bet.id, closing_line)

        logger.info(f"Updated {len(bets)} bets with closing odds for game {game_id}")

    def schedule_closing_odds_fetch(self, game: Dict, minutes_before: int = 10):
        """
        Schedule a closing odds fetch for a specific game.

        Args:
            game: Game dictionary with start_time
            minutes_before: Minutes before game to fetch (default 10)
        """
        game_id = game['game_id']

        # Avoid duplicate scheduling
        if game_id in self.scheduled_games:
            return

        # Calculate when to fetch
        start_time = game['start_time']
        fetch_time = start_time - timedelta(minutes=minutes_before)
        now = datetime.now()

        # If fetch time is in the past, fetch now
        if fetch_time <= now:
            logger.info(f"Fetching closing odds immediately for {game['home_team']} vs {game['away_team']}")
            self.fetch_and_store_closing_odds(
                game_id,
                game['sport'],
                game['home_team'],
                game['away_team']
            )
            return

        # Calculate seconds until fetch
        seconds_until_fetch = (fetch_time - now).total_seconds()

        logger.info(
            f"Scheduled closing odds fetch for {game['home_team']} vs {game['away_team']} "
            f"in {seconds_until_fetch/60:.1f} minutes"
        )

        # Schedule the job
        schedule.every(int(seconds_until_fetch)).seconds.do(
            self.fetch_and_store_closing_odds,
            game_id=game_id,
            sport=game['sport'],
            home_team=game['home_team'],
            away_team=game['away_team']
        ).tag(game_id)

        self.scheduled_games.add(game_id)

    def check_and_schedule_upcoming_games(self):
        """
        Main job: Check for upcoming games and schedule closing odds fetching.

        Run this every hour.
        """
        logger.info("Checking for upcoming games...")

        upcoming = self.get_upcoming_games(hours_ahead=2)

        logger.info(f"Found {len(upcoming)} games starting in next 2 hours")

        for game in upcoming:
            self.schedule_closing_odds_fetch(game)

    def start_scheduler(self):
        """
        Start the closing odds scheduler.

        This runs as a daemon:
        - Every hour: Check for upcoming games
        - Before each game: Fetch closing odds
        """
        logger.info("🚀 Starting closing odds scheduler...")

        # Initial check
        self.check_and_schedule_upcoming_games()

        # Schedule hourly checks
        schedule.every(1).hours.do(self.check_and_schedule_upcoming_games)

        # Run forever
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


# Alternative Approach: Continuous Polling
class ContinuousOddsPoller:
    """
    Alternative approach: Poll odds continuously and track history.

    More accurate but more API calls and storage.
    """

    def __init__(self, poll_interval_minutes: int = 30):
        """
        Initialize continuous poller.

        Args:
            poll_interval_minutes: How often to poll odds
        """
        self.poll_interval = poll_interval_minutes
        self.odds_client = OddsAPIClient()
        self.db = SessionLocal()

    def poll_and_store_odds(self):
        """
        Poll current odds and store in history table.

        Run this every 30 minutes.
        """
        logger.info("Polling current odds...")

        try:
            # Fetch all current odds
            nba_odds = self.odds_client.fetch_live_odds(sport='nba')

            # Store in OddsHistory table
            for game in nba_odds:
                # Create history record
                history = OddsHistory(
                    id=str(uuid.uuid4()),
                    game_id=game.get('game_id'),
                    sport='nba',
                    home_team=game.get('home_team'),
                    away_team=game.get('away_team'),
                    home_odds=game.get('home_odds'),
                    away_odds=game.get('away_odds'),
                    fetched_at=datetime.now()
                )
                self.db.add(history)

            self.db.commit()
            logger.info(f"Stored odds for {len(nba_odds)} games")

        except Exception as e:
            logger.error(f"Error polling odds: {e}")
            self.db.rollback()

    def get_closing_odds_from_history(self, game_id: str) -> Optional[Dict]:
        """
        Get closing odds from historical data.

        Returns the last odds recorded before game started.

        Args:
            game_id: ESPN game ID

        Returns:
            Closing odds dict or None
        """
        # Get all odds records for this game, ordered by time
        records = self.db.query(OddsHistory).filter(
            OddsHistory.game_id == game_id
        ).order_by(OddsHistory.fetched_at.desc()).all()

        if not records:
            return None

        # First record = most recent before game = closing line
        closing = records[0]

        return {
            'home_odds': closing.home_odds,
            'away_odds': closing.away_odds,
            'fetched_at': closing.fetched_at
        }


def main():
    """Example usage."""
    print("=" * 70)
    print("CLOSING ODDS FETCHER")
    print("=" * 70)
    print()

    fetcher = ClosingOddsFetcher()

    # Check upcoming games
    upcoming = fetcher.get_upcoming_games(hours_ahead=24)

    if upcoming:
        print(f"Found {len(upcoming)} upcoming games in next 24 hours:\n")
        for game in upcoming:
            print(f"  {game['home_team']} vs {game['away_team']}")
            print(f"  Starts in: {game['minutes_until_start']:.0f} minutes")
            print(f"  Start time: {game['start_time']}")
            print()
    else:
        print("No upcoming games in next 24 hours.\n")

    print("=" * 70)
    print("To run the scheduler:")
    print("  python -m analytics.closing_odds_fetcher --daemon")
    print()
    print("This will:")
    print("  1. Check for upcoming games every hour")
    print("  2. Schedule closing odds fetch 10 min before each game")
    print("  3. Update all bets with CLV data")
    print("=" * 70)


if __name__ == '__main__':
    import sys

    if '--daemon' in sys.argv:
        # Run as daemon
        fetcher = ClosingOddsFetcher()
        fetcher.start_scheduler()
    else:
        # Just show info
        main()
