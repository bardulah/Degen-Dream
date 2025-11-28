"""
Bet Recommendation Engine

Uses historical performance data to recommend high-value bets.

This engine:
1. Analyzes agent performance by sport/league
2. Identifies high-confidence opportunities
3. Calculates expected value (EV)
4. Recommends top bets based on criteria
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.schema import SessionLocal, Bet, AgentSimulationStats, Simulation
from agents.base_agent import Game
from monitoring.logger import logger


class BetRecommender:
    """Recommend bets based on historical performance."""

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize bet recommender.

        Args:
            db: Database session (optional)
        """
        self.db = db
        self._should_close_db = False

        if not self.db:
            self.db = SessionLocal()
            self._should_close_db = True

        # Thresholds for recommendations
        self.min_confidence = 0.65  # Minimum 65% confidence
        self.min_ev = 0.05  # Minimum 5% expected value
        self.min_sample_size = 10  # At least 10 historical bets

    def __del__(self):
        """Clean up database connection."""
        if self._should_close_db and self.db:
            self.db.close()

    def get_agent_performance(self, agent_name: str, sport: str, days: int = 90) -> Dict:
        """
        Get historical performance for an agent on a specific sport.

        Args:
            agent_name: Agent name
            sport: Sport type
            days: Days of history to analyze

        Returns:
            Dictionary with performance metrics
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Get bets for this agent/sport
        bets = self.db.query(Bet).filter(
            Bet.agent_name == agent_name,
            Bet.sport == sport,
            Bet.created_at >= cutoff_date,
            Bet.result_status.in_(['won', 'lost'])
        ).all()

        if len(bets) < self.min_sample_size:
            return {
                'sample_size': len(bets),
                'insufficient_data': True
            }

        # Calculate metrics
        total_bets = len(bets)
        wins = sum(1 for b in bets if b.result_status == 'won')
        total_wagered = sum(b.stake for b in bets)
        total_profit = sum(b.profit_loss for b in bets if b.profit_loss is not None)

        win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0.0
        roi = (total_profit / total_wagered) * 100 if total_wagered > 0 else 0.0

        # Average odds
        avg_odds = sum(b.odds for b in bets) / total_bets if total_bets > 0 else 0.0

        return {
            'sample_size': total_bets,
            'insufficient_data': False,
            'win_rate': win_rate,
            'roi': roi,
            'avg_odds': avg_odds,
            'total_profit': total_profit,
            'confidence_score': self._calculate_confidence_score(total_bets, win_rate, roi)
        }

    def _calculate_confidence_score(self, sample_size: int, win_rate: float, roi: float) -> float:
        """
        Calculate confidence score (0-1) based on metrics.

        Args:
            sample_size: Number of historical bets
            win_rate: Win rate percentage
            roi: ROI percentage

        Returns:
            Confidence score 0-1
        """
        # Sample size factor (0-1, caps at 100 bets)
        sample_factor = min(sample_size / 100, 1.0)

        # Win rate factor (0-1, normalized from 40-70%)
        win_rate_factor = max(0, min((win_rate - 40) / 30, 1.0))

        # ROI factor (0-1, positive ROI gets higher score)
        roi_factor = max(0, min(roi / 20, 1.0))

        # Weighted average
        confidence = (
            sample_factor * 0.3 +
            win_rate_factor * 0.4 +
            roi_factor * 0.3
        )

        return confidence

    def calculate_expected_value(self, win_prob: float, odds: float, stake: float = 100) -> float:
        """
        Calculate expected value of a bet.

        Args:
            win_prob: Probability of winning (0-1)
            odds: Decimal odds
            stake: Stake amount

        Returns:
            Expected value in currency units

        Formula: EV = (win_prob * profit) - (loss_prob * stake)
        """
        profit_if_win = stake * (odds - 1)
        loss_prob = 1 - win_prob

        ev = (win_prob * profit_if_win) - (loss_prob * stake)
        return ev

    def recommend_bets(self, games: List[Game], max_recommendations: int = 5) -> List[Dict]:
        """
        Recommend top bets from a list of games.

        Args:
            games: List of available games
            max_recommendations: Maximum number of recommendations

        Returns:
            List of recommended bets, sorted by value
        """
        recommendations = []

        # For each game, evaluate each agent
        for game in games:
            # Get unique agents from database
            agents = self.db.query(Bet.agent_name).distinct().all()

            for (agent_name,) in agents:
                # Get agent performance for this sport
                perf = self.get_agent_performance(agent_name, game.sport)

                if perf.get('insufficient_data'):
                    continue

                # Skip if performance is poor
                if perf['roi'] < 0 or perf['win_rate'] < 45:
                    continue

                # Estimate win probability from historical win rate
                win_prob = perf['win_rate'] / 100

                # Determine which team this agent would bet on
                # (Simplified - in reality you'd run the agent)
                # For now, assume home team
                bet_odds = game.home_odds
                bet_team = game.home_team

                # Calculate EV
                ev = self.calculate_expected_value(win_prob, bet_odds)
                ev_pct = (ev / 100) * 100  # As percentage

                # Skip if EV is too low
                if ev_pct < self.min_ev * 100:
                    continue

                # Create recommendation
                recommendation = {
                    'game_id': f"{game.home_team}_vs_{game.away_team}",
                    'home_team': game.home_team,
                    'away_team': game.away_team,
                    'sport': game.sport,
                    'agent_name': agent_name,
                    'bet_team': bet_team,
                    'bet_type': 'moneyline',
                    'odds': bet_odds,
                    'confidence': perf['confidence_score'],
                    'expected_value': ev,
                    'ev_percentage': ev_pct,
                    'historical_win_rate': perf['win_rate'],
                    'historical_roi': perf['roi'],
                    'sample_size': perf['sample_size'],
                    'reasoning': self._generate_reasoning(agent_name, perf, ev_pct)
                }

                recommendations.append(recommendation)

        # Sort by EV percentage (descending)
        recommendations.sort(key=lambda x: x['ev_percentage'], reverse=True)

        # Return top N
        return recommendations[:max_recommendations]

    def _generate_reasoning(self, agent_name: str, performance: Dict, ev_pct: float) -> str:
        """Generate reasoning for recommendation."""
        return (
            f"{agent_name} has {performance['win_rate']:.1f}% win rate "
            f"and {performance['roi']:+.1f}% ROI on this sport "
            f"over {performance['sample_size']} bets. "
            f"Expected value: +{ev_pct:.1f}%"
        )

    def get_top_agents_by_sport(self, sport: str, top_n: int = 3) -> List[Dict]:
        """
        Get top performing agents for a specific sport.

        Args:
            sport: Sport type
            top_n: Number of agents to return

        Returns:
            List of top agents with their stats
        """
        # Get all agent stats for this sport
        query = self.db.query(
            Bet.agent_name,
            func.count(Bet.id).label('total_bets'),
            func.sum(func.case((Bet.result_status == 'won',  1), else_=0)).label('wins'),
            func.sum(Bet.profit_loss).label('total_profit'),
            func.sum(Bet.stake).label('total_wagered')
        ).filter(
            Bet.sport == sport,
            Bet.result_status.in_(['won', 'lost'])
        ).group_by(Bet.agent_name).all()

        agents = []
        for agent_name, total_bets, wins, total_profit, total_wagered in query:
            if total_bets < self.min_sample_size:
                continue

            win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0.0
            roi = (total_profit / total_wagered) * 100 if total_wagered > 0 else 0.0

            agents.append({
                'agent_name': agent_name,
                'total_bets': total_bets,
                'win_rate': win_rate,
                'roi': roi,
                'total_profit': total_profit
            })

        # Sort by ROI
        agents.sort(key=lambda x: x['roi'], reverse=True)

        return agents[:top_n]


def main():
    """Example usage."""
    recommender = BetRecommender()

    print("=" * 70)
    print("BET RECOMMENDATION ENGINE")
    print("=" * 70)
    print()

    # Example: Get top agents by sport
    print("Top NBA Agents:")
    print("-" * 70)

    top_agents = recommender.get_top_agents_by_sport('nba', top_n=3)

    if top_agents:
        for i, agent in enumerate(top_agents, 1):
            print(f"{i}. {agent['agent_name']}")
            print(f"   Win Rate: {agent['win_rate']:.1f}%")
            print(f"   ROI: {agent['roi']:+.2f}%")
            print(f"   Profit: €{agent['total_profit']:+,.2f}")
            print(f"   Sample: {agent['total_bets']} bets")
            print()
    else:
        print("No agents with sufficient data yet.\n")

    print("=" * 70)
    print("💡 Run simulations to build agent history for recommendations")
    print("=" * 70)


if __name__ == '__main__':
    main()
