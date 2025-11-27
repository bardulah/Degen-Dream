"""
Historical Performance Analyzer

Analyze betting performance over time to identify:
- Trends and patterns
- Best/worst performing sports
- Time-based edges (weekday vs weekend)
- Streak analysis
- Sharpe ratio and risk metrics
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from database.schema import SessionLocal, Bet, Simulation, AgentSimulationStats
from monitoring.logger import logger


class PerformanceAnalyzer:
    """Analyze historical betting performance."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize performance analyzer."""
        self.db = db
        self._should_close_db = False

        if not self.db:
            self.db = SessionLocal()
            self._should_close_db = True

    def __del__(self):
        """Clean up database connection."""
        if self._should_close_db and self.db:
            self.db.close()

    def calculate_sharpe_ratio(self, simulation_id: Optional[str] = None, days: int = 90) -> float:
        """
        Calculate Sharpe Ratio (risk-adjusted returns).

        Args:
            simulation_id: Optional simulation to analyze
            days: Days of history if no simulation specified

        Returns:
            Sharpe ratio

        Formula: (Mean Return - Risk-Free Rate) / Std Dev of Returns
        """
        # Get bets
        query = self.db.query(Bet).filter(
            Bet.result_status.in_(['won', 'lost']),
            Bet.profit_loss.isnot(None)
        )

        if simulation_id:
            query = query.filter(Bet.simulation_id == simulation_id)
        else:
            cutoff = datetime.now() - timedelta(days=days)
            query = query.filter(Bet.created_at >= cutoff)

        bets = query.all()

        if len(bets) < 2:
            return 0.0

        # Calculate returns as percentage of stake
        returns = [b.profit_loss / b.stake for b in bets]

        # Mean return
        mean_return = sum(returns) / len(returns)

        # Standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        # Sharpe ratio (assuming risk-free rate = 0 for simplicity)
        sharpe = mean_return / std_dev

        # Annualize (assuming ~250 betting days per year)
        sharpe_annual = sharpe * math.sqrt(250)

        return sharpe_annual

    def calculate_max_drawdown(self, simulation_id: Optional[str] = None) -> Dict:
        """
        Calculate maximum drawdown (worst losing streak).

        Args:
            simulation_id: Optional simulation to analyze

        Returns:
            Dictionary with drawdown metrics
        """
        query = self.db.query(Bet).filter(
            Bet.result_status.in_(['won', 'lost']),
            Bet.profit_loss.isnot(None)
        ).order_by(Bet.created_at)

        if simulation_id:
            query = query.filter(Bet.simulation_id == simulation_id)

        bets = query.all()

        if not bets:
            return {'max_drawdown': 0.0, 'max_drawdown_pct': 0.0}

        # Calculate running bankroll
        initial_bankroll = 10000  # Starting point
        running_bankroll = initial_bankroll
        peak_bankroll = initial_bankroll
        max_drawdown = 0.0

        for bet in bets:
            running_bankroll += bet.profit_loss

            # Update peak
            if running_bankroll > peak_bankroll:
                peak_bankroll = running_bankroll

            # Calculate drawdown from peak
            drawdown = peak_bankroll - running_bankroll
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_pct = (max_drawdown / peak_bankroll) * 100 if peak_bankroll > 0 else 0.0

        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'peak_bankroll': peak_bankroll
        }

    def analyze_by_sport(self, days: int = 90) -> Dict[str, Dict]:
        """
        Analyze performance broken down by sport.

        Args:
            days: Days of history to analyze

        Returns:
            Dictionary of sport -> performance metrics
        """
        cutoff = datetime.now() - timedelta(days=days)

        bets = self.db.query(Bet).filter(
            Bet.result_status.in_(['won', 'lost']),
            Bet.created_at >= cutoff
        ).all()

        # Group by sport
        sports = {}
        for bet in bets:
            sport = bet.sport or 'unknown'
            if sport not in sports:
                sports[sport] = []
            sports[sport].append(bet)

        # Calculate metrics for each sport
        sport_stats = {}
        for sport, sport_bets in sports.items():
            total_bets = len(sport_bets)
            wins = sum(1 for b in sport_bets if b.result_status == 'won')
            total_wagered = sum(b.stake for b in sport_bets)
            total_profit = sum(b.profit_loss for b in sport_bets if b.profit_loss is not None)

            win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0.0
            roi = (total_profit / total_wagered) * 100 if total_wagered > 0 else 0.0

            sport_stats[sport] = {
                'total_bets': total_bets,
                'wins': wins,
                'losses': total_bets - wins,
                'win_rate': win_rate,
                'roi': roi,
                'total_profit': total_profit,
                'total_wagered': total_wagered
            }

        return sport_stats

    def analyze_by_bet_type(self, days: int = 90) -> Dict[str, Dict]:
        """Analyze performance by bet type (moneyline, spread, total)."""
        cutoff = datetime.now() - timedelta(days=days)

        bets = self.db.query(Bet).filter(
            Bet.result_status.in_(['won', 'lost']),
            Bet.created_at >= cutoff
        ).all()

        # Group by bet type
        bet_types = {}
        for bet in bets:
            bet_type = bet.bet_type.value if bet.bet_type else 'unknown'
            if bet_type not in bet_types:
                bet_types[bet_type] = []
            bet_types[bet_type].append(bet)

        # Calculate metrics
        type_stats = {}
        for bet_type, type_bets in bet_types.items():
            total_bets = len(type_bets)
            wins = sum(1 for b in type_bets if b.result_status == 'won')
            total_wagered = sum(b.stake for b in type_bets)
            total_profit = sum(b.profit_loss for b in type_bets if b.profit_loss is not None)

            win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0.0
            roi = (total_profit / total_wagered) * 100 if total_wagered > 0 else 0.0

            type_stats[bet_type] = {
                'total_bets': total_bets,
                'win_rate': win_rate,
                'roi': roi,
                'total_profit': total_profit
            }

        return type_stats

    def find_streaks(self, simulation_id: Optional[str] = None) -> Dict:
        """
        Find win/loss streaks.

        Args:
            simulation_id: Optional simulation to analyze

        Returns:
            Dictionary with streak information
        """
        query = self.db.query(Bet).filter(
            Bet.result_status.in_(['won', 'lost'])
        ).order_by(Bet.created_at)

        if simulation_id:
            query = query.filter(Bet.simulation_id == simulation_id)

        bets = query.all()

        if not bets:
            return {'max_win_streak': 0, 'max_loss_streak': 0}

        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0

        for bet in bets:
            if bet.result_status == 'won':
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)

        return {
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak,
            'current_win_streak': current_win_streak,
            'current_loss_streak': current_loss_streak
        }

    def analyze_time_patterns(self, days: int = 90) -> Dict:
        """
        Analyze performance by day of week.

        Args:
            days: Days of history to analyze

        Returns:
            Dictionary of day -> performance metrics
        """
        cutoff = datetime.now() - timedelta(days=days)

        bets = self.db.query(Bet).filter(
            Bet.result_status.in_(['won', 'lost']),
            Bet.created_at >= cutoff
        ).all()

        # Group by day of week
        days_of_week = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday
        for bet in bets:
            day = bet.created_at.weekday()
            days_of_week[day].append(bet)

        # Calculate metrics
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_stats = {}

        for day_num, day_bets in days_of_week.items():
            if not day_bets:
                continue

            total_bets = len(day_bets)
            wins = sum(1 for b in day_bets if b.result_status == 'won')
            total_profit = sum(b.profit_loss for b in day_bets if b.profit_loss is not None)
            total_wagered = sum(b.stake for b in day_bets)

            win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0.0
            roi = (total_profit / total_wagered) * 100 if total_wagered > 0 else 0.0

            day_stats[day_names[day_num]] = {
                'total_bets': total_bets,
                'win_rate': win_rate,
                'roi': roi,
                'total_profit': total_profit
            }

        return day_stats

    def generate_performance_report(self, simulation_id: Optional[str] = None) -> Dict:
        """
        Generate comprehensive performance report.

        Args:
            simulation_id: Optional simulation to analyze

        Returns:
            Complete performance report
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'sharpe_ratio': self.calculate_sharpe_ratio(simulation_id),
            'max_drawdown': self.calculate_max_drawdown(simulation_id),
            'streaks': self.find_streaks(simulation_id),
            'by_sport': self.analyze_by_sport(),
            'by_bet_type': self.analyze_by_bet_type(),
            'by_day_of_week': self.analyze_time_patterns()
        }

        return report


def main():
    """Example usage."""
    analyzer = PerformanceAnalyzer()

    print("=" * 70)
    print("PERFORMANCE ANALYZER")
    print("=" * 70)
    print()

    # Generate report
    report = analyzer.generate_performance_report()

    print(f"📊 Report Generated: {report['generated_at']}\n")

    print("Risk Metrics:")
    print("-" * 70)
    print(f"  Sharpe Ratio:     {report['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown:     €{report['max_drawdown']['max_drawdown']:.2f}")
    print(f"  Max Drawdown %:   {report['max_drawdown']['max_drawdown_pct']:.1f}%")
    print()

    print("Streaks:")
    print("-" * 70)
    print(f"  Max Win Streak:   {report['streaks']['max_win_streak']}")
    print(f"  Max Loss Streak:  {report['streaks']['max_loss_streak']}")
    print()

    print("By Sport:")
    print("-" * 70)
    for sport, stats in report['by_sport'].items():
        print(f"  {sport}:")
        print(f"    Win Rate: {stats['win_rate']:.1f}%")
        print(f"    ROI: {stats['roi']:+.2f}%")
        print(f"    Bets: {stats['total_bets']}")
    print()

    print("=" * 70)


if __name__ == '__main__':
    main()
