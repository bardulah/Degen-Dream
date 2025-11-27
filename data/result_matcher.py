"""
Result Matcher - Fetches live scores and matches them to bets in the database.

This module:
1. Fetches finished match scores from ESPN API
2. Matches them to bets in the database
3. Updates bet results and calculates P&L
4. Updates simulation and agent statistics
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from difflib import SequenceMatcher
import time

from sports_score_fetcher import SportsScoreFetcher
from database.schema import Bet, Simulation, AgentSimulationStats, SessionLocal
from monitoring.logger import logger


class ResultMatcher:
    """Matches live scores to bets and updates results."""

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the result matcher.

        Args:
            db: Database session (optional, will create one if not provided)
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

    def _normalize_team_name(self, team_name: str) -> str:
        """
        Normalize team name for matching.

        Args:
            team_name: Team name to normalize

        Returns:
            Normalized team name (lowercase, no special chars)
        """
        return team_name.lower().strip().replace('.', '').replace('-', ' ')

    def _match_team_names(self, name1: str, name2: str, threshold: float = 0.7) -> bool:
        """
        Check if two team names match using fuzzy matching.

        Args:
            name1: First team name
            name2: Second team name
            threshold: Match threshold (0.0-1.0)

        Returns:
            True if names match above threshold
        """
        norm1 = self._normalize_team_name(name1)
        norm2 = self._normalize_team_name(name2)

        # Exact match
        if norm1 == norm2:
            return True

        # Check if one contains the other (e.g., "LA Lakers" vs "Lakers")
        if norm1 in norm2 or norm2 in norm1:
            return True

        # Fuzzy match
        ratio = SequenceMatcher(None, norm1, norm2).ratio()
        return ratio >= threshold

    def _determine_bet_result(self, bet: Bet, game: Dict) -> Tuple[str, Optional[float]]:
        """
        Determine if a bet won, lost, or pushed.

        Args:
            bet: Bet object from database
            game: Game info dict from ESPN API

        Returns:
            Tuple of (result_status, profit_loss)
        """
        home_score = game['home_score']
        away_score = game['away_score']
        winner = game['winner']

        # Determine actual winner for the bet
        bet_won = False

        if bet.bet_type.value == 'moneyline':
            # Simple moneyline bet
            if self._match_team_names(bet.bet_team, winner):
                bet_won = True
            elif winner == 'TIE':
                # Push on tie for moneyline
                return ('push', 0.0)

        elif bet.bet_type.value == 'spread':
            # Spread bet - need to check the line
            # Determine which team is home/away for this bet
            is_home_bet = self._match_team_names(bet.bet_team, bet.game_home_team)

            if is_home_bet:
                adjusted_home_score = home_score + bet.line
                bet_won = adjusted_home_score > away_score
                if adjusted_home_score == away_score:
                    return ('push', 0.0)
            else:
                adjusted_away_score = away_score + bet.line
                bet_won = adjusted_away_score > home_score
                if adjusted_away_score == home_score:
                    return ('push', 0.0)

        elif bet.bet_type.value == 'total':
            # Over/Under bet
            total_score = home_score + away_score
            # Assuming bet_team contains "over" or "under"
            is_over = 'over' in bet.bet_team.lower()

            if is_over:
                bet_won = total_score > bet.line
                if total_score == bet.line:
                    return ('push', 0.0)
            else:
                bet_won = total_score < bet.line
                if total_score == bet.line:
                    return ('push', 0.0)

        # Calculate P&L
        if bet_won:
            profit = bet.stake * (bet.odds - 1)
            return ('won', profit)
        else:
            return ('lost', -bet.stake)

    def _map_sport_to_espn(self, sport: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Map internal sport names to ESPN API sport/league codes.

        Args:
            sport: Internal sport identifier

        Returns:
            Tuple of (sport_type, league_code) for ESPN API
        """
        sport_lower = sport.lower()

        # Basketball
        if 'nba' in sport_lower or 'basketball' in sport_lower:
            return ('basketball', 'nba')

        # Hockey
        if 'nhl' in sport_lower or 'hockey' in sport_lower:
            return ('hockey', 'nhl')

        # Soccer
        if 'epl' in sport_lower or 'premier' in sport_lower:
            return ('soccer', 'eng.1')
        if 'mls' in sport_lower:
            return ('soccer', 'usa.1')
        if 'la_liga' in sport_lower or 'laliga' in sport_lower:
            return ('soccer', 'esp.1')
        if 'bundesliga' in sport_lower:
            return ('soccer', 'ger.1')
        if 'serie_a' in sport_lower or 'seriea' in sport_lower:
            return ('soccer', 'ita.1')
        if 'ligue_1' in sport_lower or 'ligue1' in sport_lower:
            return ('soccer', 'fra.1')
        if 'champions' in sport_lower or 'ucl' in sport_lower:
            return ('soccer', 'uefa.champions')
        if 'soccer' in sport_lower:
            # Default to EPL for generic soccer
            return ('soccer', 'eng.1')

        logger.warning(f"Unknown sport: {sport}, cannot map to ESPN API")
        return (None, None)

    def fetch_and_update_results(self, date_str: str, simulation_id: Optional[str] = None) -> Dict:
        """
        Fetch results for a specific date and update bets.

        Args:
            date_str: Date in YYYYMMDD format
            simulation_id: Optional simulation ID to limit updates

        Returns:
            Dictionary with update statistics
        """
        stats = {
            'total_checked': 0,
            'updated': 0,
            'won': 0,
            'lost': 0,
            'push': 0,
            'errors': 0
        }

        # Get pending bets for this date
        query = self.db.query(Bet).filter(
            Bet.game_date == date_str,
            Bet.result_status.in_([None, 'pending'])
        )

        if simulation_id:
            query = query.filter(Bet.simulation_id == simulation_id)

        pending_bets = query.all()
        stats['total_checked'] = len(pending_bets)

        if not pending_bets:
            logger.info(f"No pending bets found for date {date_str}")
            return stats

        logger.info(f"Checking {len(pending_bets)} pending bets for {date_str}")

        # Group bets by sport to minimize API calls
        bets_by_sport = {}
        for bet in pending_bets:
            sport_key = bet.sport or 'unknown'
            if sport_key not in bets_by_sport:
                bets_by_sport[sport_key] = []
            bets_by_sport[sport_key].append(bet)

        # Fetch scores for each sport
        for sport, bets in bets_by_sport.items():
            sport_type, league_code = self._map_sport_to_espn(sport)

            if not sport_type or not league_code:
                logger.warning(f"Skipping {len(bets)} bets - unknown sport: {sport}")
                stats['errors'] += len(bets)
                continue

            try:
                # Fetch scores from ESPN
                if sport_type == 'basketball':
                    games = self.fetcher.get_nba_scores(date_str)
                elif sport_type == 'hockey':
                    games = self.fetcher.get_nhl_scores(date_str)
                elif sport_type == 'soccer':
                    games = self.fetcher.get_soccer_scores(league_code, date_str)
                else:
                    logger.warning(f"Unknown sport type: {sport_type}")
                    continue

                logger.info(f"Found {len(games)} finished games for {sport}")

                # Match bets to games
                for bet in bets:
                    matched_game = None

                    for game in games:
                        # Try to match home and away teams
                        home_match = self._match_team_names(bet.game_home_team, game['home_team'])
                        away_match = self._match_team_names(bet.game_away_team, game['away_team'])

                        if home_match and away_match:
                            matched_game = game
                            break

                    if matched_game:
                        # Determine result
                        result_status, profit_loss = self._determine_bet_result(bet, matched_game)

                        # Update bet
                        bet.home_score = matched_game['home_score']
                        bet.away_score = matched_game['away_score']
                        bet.actual_winner = matched_game['winner']
                        bet.result_status = result_status
                        bet.profit_loss = profit_loss
                        bet.result_fetched_at = datetime.utcnow()
                        bet.game_id_espn = matched_game.get('game_id')

                        stats['updated'] += 1
                        if result_status == 'won':
                            stats['won'] += 1
                        elif result_status == 'lost':
                            stats['lost'] += 1
                        elif result_status == 'push':
                            stats['push'] += 1

                        logger.info(f"Updated bet {bet.id[:8]}: {result_status} ({profit_loss:+.2f})")
                    else:
                        logger.warning(
                            f"No match found for bet {bet.id[:8]}: "
                            f"{bet.game_away_team} @ {bet.game_home_team}"
                        )
                        stats['errors'] += 1

                # Add delay between sport API calls
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching scores for {sport}: {e}")
                stats['errors'] += len(bets)
                continue

        # Commit all updates
        try:
            self.db.commit()
            logger.info(f"Updated {stats['updated']} bets: {stats['won']} won, {stats['lost']} lost, {stats['push']} push")
        except Exception as e:
            logger.error(f"Error committing updates: {e}")
            self.db.rollback()
            raise

        return stats

    def update_simulation_stats(self, simulation_id: str) -> Dict:
        """
        Update simulation statistics based on bet results.

        Args:
            simulation_id: Simulation ID to update

        Returns:
            Dictionary with updated statistics
        """
        simulation = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()

        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        # Get all bets for this simulation
        bets = self.db.query(Bet).filter(Bet.simulation_id == simulation_id).all()

        # Calculate statistics
        total_bets = len(bets)
        settled_bets = [b for b in bets if b.result_status in ['won', 'lost', 'push']]
        won_bets = [b for b in settled_bets if b.result_status == 'won']
        lost_bets = [b for b in settled_bets if b.result_status == 'lost']

        total_wagered = sum(b.stake for b in bets)
        total_profit = sum(b.profit_loss for b in settled_bets if b.profit_loss is not None)

        win_rate = (len(won_bets) / len(settled_bets) * 100) if settled_bets else 0.0
        roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0.0
        final_bankroll = simulation.starting_bankroll + total_profit

        # Update simulation
        simulation.total_bets = total_bets
        simulation.total_wagered = total_wagered
        simulation.bets_settled = len(settled_bets)
        simulation.win_rate = win_rate
        simulation.roi = roi
        simulation.profit = total_profit
        simulation.final_bankroll = final_bankroll
        simulation.last_result_check = datetime.utcnow()

        # Update status
        if len(settled_bets) == total_bets:
            simulation.status = 'completed'
        else:
            simulation.status = 'awaiting_results'

        self.db.commit()

        logger.info(
            f"Updated simulation {simulation_id[:8]}: "
            f"{len(settled_bets)}/{total_bets} settled, "
            f"ROI: {roi:+.2f}%, Win Rate: {win_rate:.1f}%"
        )

        return {
            'simulation_id': simulation_id,
            'total_bets': total_bets,
            'settled_bets': len(settled_bets),
            'won': len(won_bets),
            'lost': len(lost_bets),
            'win_rate': win_rate,
            'roi': roi,
            'profit': total_profit,
            'final_bankroll': final_bankroll
        }

    def update_agent_stats(self, simulation_id: str) -> List[Dict]:
        """
        Update agent statistics based on bet results.

        Args:
            simulation_id: Simulation ID to update

        Returns:
            List of updated agent statistics
        """
        # Get all bets for this simulation
        bets = self.db.query(Bet).filter(Bet.simulation_id == simulation_id).all()

        # Group by agent
        agent_bets = {}
        for bet in bets:
            if bet.agent_name not in agent_bets:
                agent_bets[bet.agent_name] = []
            agent_bets[bet.agent_name].append(bet)

        updated_agents = []

        for agent_name, agent_bet_list in agent_bets.items():
            # Calculate statistics
            settled = [b for b in agent_bet_list if b.result_status in ['won', 'lost', 'push']]
            won = [b for b in settled if b.result_status == 'won']
            lost = [b for b in settled if b.result_status == 'lost']

            total_wagered = sum(b.stake for b in agent_bet_list)
            total_profit = sum(b.profit_loss for b in settled if b.profit_loss is not None)

            win_rate = (len(won) / len(settled) * 100) if settled else 0.0
            roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0.0

            # Find or create agent stats record
            agent_stats = self.db.query(AgentSimulationStats).filter(
                AgentSimulationStats.simulation_id == simulation_id,
                AgentSimulationStats.agent_name == agent_name
            ).first()

            if agent_stats:
                # Update existing
                agent_stats.total_bets = len(agent_bet_list)
                agent_stats.wins = len(won)
                agent_stats.losses = len(lost)
                agent_stats.win_rate = win_rate
                agent_stats.roi = roi
                agent_stats.profit_loss = total_profit
                agent_stats.final_bankroll = agent_stats.initial_bankroll + total_profit
            else:
                logger.warning(f"No agent stats found for {agent_name} in simulation {simulation_id[:8]}")

            updated_agents.append({
                'agent_name': agent_name,
                'total_bets': len(agent_bet_list),
                'wins': len(won),
                'losses': len(lost),
                'win_rate': win_rate,
                'roi': roi,
                'profit': total_profit
            })

        self.db.commit()
        logger.info(f"Updated stats for {len(updated_agents)} agents")

        return updated_agents


def main():
    """Example usage of ResultMatcher."""
    matcher = ResultMatcher()

    # Example: Check yesterday's games
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    print(f"Checking results for {yesterday}...")

    stats = matcher.fetch_and_update_results(yesterday)

    print(f"\nResults:")
    print(f"  Checked: {stats['total_checked']} bets")
    print(f"  Updated: {stats['updated']} bets")
    print(f"  Won: {stats['won']} | Lost: {stats['lost']} | Push: {stats['push']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
