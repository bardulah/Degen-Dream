"""
Closing Line Value (CLV) Tracker

CLV is the #1 indicator of long-term profitability in sports betting.
If you consistently beat the closing line, you're a winning bettor.

This module:
1. Fetches closing odds before games start
2. Compares them to your bet odds
3. Calculates CLV percentage
4. Tracks CLV performance over time
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from database.schema import SessionLocal, Bet, Simulation
from sports_score_fetcher import SportsScoreFetcher
from monitoring.logger import logger


class CLVTracker:
    """Track Closing Line Value for bets."""

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize CLV tracker.

        Args:
            db: Database session (optional)
        """
        self.fetcher = SportsScoreFetcher()
        self.db = db
        self._should_close_db = False

        if not self.db:
            self.db = SessionLocal()
            self._should_close_db = True

    def __del__(self):
        """Clean up database connection."""
        if self._should_close_db and self.db:
            self.db.close()

    def calculate_clv(self, bet_odds: float, closing_odds: float) -> float:
        """
        Calculate CLV percentage.

        Args:
            bet_odds: Odds when bet was placed
            closing_odds: Odds at game time (closing line)

        Returns:
            CLV percentage (positive = beat the closing line)

        Example:
            Bet at 2.10, closing line 2.00
            CLV = (2.10 - 2.00) / 2.00 * 100 = +5.0%
        """
        if closing_odds == 0:
            return 0.0

        clv = ((bet_odds - closing_odds) / closing_odds) * 100
        return clv

    def fetch_closing_odds(self, game_id_espn: str, bet_team: str, sport: str) -> Optional[float]:
        """
        Fetch closing odds for a specific game/team.

        Args:
            game_id_espn: ESPN game ID
            bet_team: Team that was bet on
            sport: Sport type

        Returns:
            Closing odds, or None if not available
        """
        # This would need to be called right before game time
        # For now, we'll use a simplified version that fetches from ESPN

        # In a real implementation, you'd want to:
        # 1. Store odds over time
        # 2. Fetch the last odds before game starts
        # 3. Compare to your bet odds

        # Placeholder: Return None (implement when you have real-time odds tracking)
        return None

    def update_bet_clv(self, bet_id: str, closing_odds: float):
        """
        Update CLV for a specific bet.

        Args:
            bet_id: Bet UUID
            closing_odds: Closing line odds
        """
        bet = self.db.query(Bet).filter(Bet.id == bet_id).first()

        if not bet:
            raise ValueError(f"Bet {bet_id} not found")

        # Calculate CLV
        clv = self.calculate_clv(bet.odds, closing_odds)
        beat_line = bet.odds > closing_odds

        # Update bet
        bet.closing_odds = closing_odds
        bet.clv_percentage = clv
        bet.beat_closing_line = beat_line

        self.db.commit()

        logger.info(
            f"Updated CLV for bet {bet_id[:8]}: "
            f"Bet @ {bet.odds} vs Closing @ {closing_odds} = "
            f"{clv:+.2f}% CLV ({'✅ BEAT' if beat_line else '❌ LOST'})"
        )

    def get_clv_stats(self, simulation_id: Optional[str] = None, days: int = 30) -> Dict:
        """
        Get CLV statistics.

        Args:
            simulation_id: Optional simulation to limit to
            days: Number of days back to analyze

        Returns:
            Dictionary with CLV statistics
        """
        # Build query
        query = self.db.query(Bet).filter(
            Bet.closing_odds.isnot(None),
            Bet.clv_percentage.isnot(None)
        )

        if simulation_id:
            query = query.filter(Bet.simulation_id == simulation_id)
        else:
            # Last N days
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(Bet.created_at >= cutoff_date)

        bets = query.all()

        if not bets:
            return {
                'total_bets': 0,
                'average_clv': 0.0,
                'beat_closing_line_pct': 0.0,
                'positive_clv_count': 0,
                'negative_clv_count': 0
            }

        # Calculate stats
        total_bets = len(bets)
        beat_line_count = sum(1 for b in bets if b.beat_closing_line)
        total_clv = sum(b.clv_percentage for b in bets)
        positive_clv_count = sum(1 for b in bets if b.clv_percentage > 0)
        negative_clv_count = sum(1 for b in bets if b.clv_percentage < 0)

        return {
            'total_bets': total_bets,
            'average_clv': total_clv / total_bets if total_bets > 0 else 0.0,
            'beat_closing_line_pct': (beat_line_count / total_bets * 100) if total_bets > 0 else 0.0,
            'positive_clv_count': positive_clv_count,
            'negative_clv_count': negative_clv_count,
            'best_clv': max(b.clv_percentage for b in bets),
            'worst_clv': min(b.clv_percentage for b in bets)
        }

    def get_clv_by_sport(self, days: int = 30) -> Dict[str, Dict]:
        """
        Get CLV statistics broken down by sport.

        Args:
            days: Number of days back to analyze

        Returns:
            Dictionary of sport -> CLV stats
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        bets = self.db.query(Bet).filter(
            Bet.closing_odds.isnot(None),
            Bet.clv_percentage.isnot(None),
            Bet.created_at >= cutoff_date
        ).all()

        # Group by sport
        sports = {}
        for bet in bets:
            sport = bet.sport or 'unknown'
            if sport not in sports:
                sports[sport] = []
            sports[sport].append(bet)

        # Calculate stats for each sport
        stats_by_sport = {}
        for sport, sport_bets in sports.items():
            total = len(sport_bets)
            beat_count = sum(1 for b in sport_bets if b.beat_closing_line)
            avg_clv = sum(b.clv_percentage for b in sport_bets) / total

            stats_by_sport[sport] = {
                'total_bets': total,
                'average_clv': avg_clv,
                'beat_closing_line_pct': (beat_count / total * 100) if total > 0 else 0.0
            }

        return stats_by_sport

    def analyze_clv_vs_results(self) -> Dict:
        """
        Analyze correlation between CLV and actual bet results.

        Returns:
            Dictionary showing if beating closing line = winning
        """
        bets = self.db.query(Bet).filter(
            Bet.closing_odds.isnot(None),
            Bet.clv_percentage.isnot(None),
            Bet.result_status.in_(['won', 'lost'])
        ).all()

        if not bets:
            return {'error': 'No bets with both CLV and results'}

        # Split by CLV
        positive_clv = [b for b in bets if b.beat_closing_line]
        negative_clv = [b for b in bets if not b.beat_closing_line]

        # Calculate win rates
        positive_clv_wins = sum(1 for b in positive_clv if b.result_status == 'won')
        negative_clv_wins = sum(1 for b in negative_clv if b.result_status == 'won')

        return {
            'positive_clv': {
                'total': len(positive_clv),
                'wins': positive_clv_wins,
                'win_rate': (positive_clv_wins / len(positive_clv) * 100) if positive_clv else 0.0
            },
            'negative_clv': {
                'total': len(negative_clv),
                'wins': negative_clv_wins,
                'win_rate': (negative_clv_wins / len(negative_clv) * 100) if negative_clv else 0.0
            }
        }


def main():
    """Example usage and testing."""
    tracker = CLVTracker()

    print("=" * 70)
    print("CLOSING LINE VALUE (CLV) TRACKER")
    print("=" * 70)
    print()

    # Example: Calculate CLV
    print("Example CLV Calculation:")
    print("-" * 70)

    examples = [
        (2.10, 2.00, "Beat the closing line"),
        (2.00, 2.10, "Lost to the closing line"),
        (1.85, 1.85, "Matched the closing line"),
    ]

    for bet_odds, closing_odds, desc in examples:
        clv = tracker.calculate_clv(bet_odds, closing_odds)
        print(f"  Bet @ {bet_odds} → Closing @ {closing_odds}")
        print(f"  CLV: {clv:+.2f}% ({desc})")
        print()

    # Get CLV stats
    print("=" * 70)
    print("CLV STATISTICS (Last 30 Days)")
    print("=" * 70)

    stats = tracker.get_clv_stats(days=30)

    if stats['total_bets'] > 0:
        print(f"Total Bets:          {stats['total_bets']}")
        print(f"Average CLV:         {stats['average_clv']:+.2f}%")
        print(f"Beat Closing Line:   {stats['beat_closing_line_pct']:.1f}%")
        print(f"Positive CLV Bets:   {stats['positive_clv_count']}")
        print(f"Negative CLV Bets:   {stats['negative_clv_count']}")
        print(f"Best CLV:            {stats['best_clv']:+.2f}%")
        print(f"Worst CLV:           {stats['worst_clv']:+.2f}%")
    else:
        print("No bets with CLV data yet.")
        print()
        print("💡 CLV data is added when closing odds are recorded.")
        print("   Set up automated odds tracking to populate CLV.")

    print()
    print("=" * 70)


if __name__ == '__main__':
    main()
