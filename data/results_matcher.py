"""Match real match results with placed bets."""

import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz
from database.schema import Bet, BetOutcome
from agents.base_agent import Game


class ResultsMatcher:
    """Matches real match results with betting records."""
    
    def __init__(self):
        """Initialize results matcher."""
        self.api_key = "FLASHSCORE_API_KEY"  # Placeholder - would use Flashscore API
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def match_results(self, bets: List[Bet], games: List[Game]) -> List[Tuple[Bet, BetOutcome, float]]:
        """Match bet results based on real game outcomes.
        
        Args:
            bets: List of PENDING bets from database
            games: List of real Game results with scores
        
        Returns:
            List of tuples: (Bet, Outcome, Profit/Loss)
        """
        results = []
        
        for bet in bets:
            # Find matching game
            matching_game = self._find_matching_game(bet, games)
            
            if not matching_game:
                print(f"⚠️  Could not match {bet.agent_name}'s bet: {bet.game_home_team} vs {bet.game_away_team}")
                continue
            
            # Settle the bet based on result
            outcome, profit_loss = self._settle_bet(bet, matching_game)
            results.append((bet, outcome, profit_loss))
        
        return results
    
    def _find_matching_game(self, bet: Bet, games: List[Game]) -> Optional[Game]:
        """Find real game result matching a bet.
        
        Handles:
        - Team name variations (City vs Manchester City)
        - Accent differences
        - Abbreviations
        
        Args:
            bet: Bet record with team names
            games: List of available game results
        
        Returns:
            Matching Game object or None
        """
        # Exact match first
        for game in games:
            if (self._normalize_team(bet.game_home_team) == self._normalize_team(game.home_team) and
                self._normalize_team(bet.game_away_team) == self._normalize_team(game.away_team)):
                return game
        
        # Fuzzy match if no exact match
        best_match = None
        best_score = 0.0
        
        for game in games:
            # Compare home team (must be reasonably close)
            home_score = self._fuzzy_match(bet.game_home_team, game.home_team)
            away_score = self._fuzzy_match(bet.game_away_team, game.away_team)
            
            # Both teams must match reasonably well
            combined_score = (home_score + away_score) / 2
            
            # Lower threshold for basketball teams (shorter names like "Lakers")
            threshold = 0.6 if len(bet.game_home_team.split()) <= 2 else 0.75
            
            if combined_score > best_score and combined_score > threshold:
                best_match = game
                best_score = combined_score
        
        return best_match
    
    def _settle_bet(self, bet: Bet, game: Game) -> Tuple[BetOutcome, float]:
        """Calculate bet outcome and P&L.
        
        Args:
            bet: Placed bet
            game: Game result
        
        Returns:
            Tuple of (Outcome enum, Profit/Loss amount)
        """
        # Get team names normalized
        home = self._normalize_team(bet.game_home_team)
        away = self._normalize_team(bet.game_away_team)
        bet_team = self._normalize_team(bet.bet_team)
        
        # Get scores from game result
        home_score = getattr(game, 'home_score', None)
        away_score = getattr(game, 'away_score', None)
        
        if home_score is None or away_score is None:
            # No score available yet
            return BetOutcome.PENDING, 0.0
        
        # Determine winner
        if home_score > away_score:
            winner = home
        elif away_score > home_score:
            winner = away
        else:
            winner = "DRAW"
        
        # Check bet type and calculate outcome
        if bet.bet_type == "moneyline":
            outcome = self._settle_moneyline(bet_team, winner, home_score, away_score)
        elif bet.bet_type == "spread":
            outcome = self._settle_spread(bet_team, bet.line, home_score, away_score)
        elif bet.bet_type == "total":
            outcome = self._settle_total(bet_team, bet.line, home_score, away_score)
        else:
            return BetOutcome.PUSH, 0.0
        
        # Calculate profit/loss
        if outcome == BetOutcome.WON:
            profit = bet.stake * (bet.odds - 1)
            return BetOutcome.WON, profit
        elif outcome == BetOutcome.LOST:
            return BetOutcome.LOST, -bet.stake
        else:  # PUSH
            return BetOutcome.PUSH, 0.0
    
    def _settle_moneyline(self, bet_team: str, winner: str, home_score: int, away_score: int) -> BetOutcome:
        """Settle moneyline bet.
        
        Args:
            bet_team: Team bet on
            winner: Actual winner (team name or "DRAW")
            home_score: Home team score
            away_score: Away team score
        
        Returns:
            Outcome enum
        """
        if bet_team == winner:
            return BetOutcome.WON
        elif winner == "DRAW" and bet_team == "DRAW":
            return BetOutcome.WON
        else:
            return BetOutcome.LOST
    
    def _settle_spread(self, bet_team: str, line: float, home_score: int, away_score: int) -> BetOutcome:
        """Settle spread bet.
        
        Args:
            bet_team: Team bet on (with spread)
            line: Spread line (negative = favorite)
            home_score: Home team score
            away_score: Away team score
        
        Returns:
            Outcome enum
        """
        # Simplified: line tells us which team and margin
        # Negative line = home team is favorite
        # Positive line = away team is favorite
        
        if line < 0:
            # Home team favored
            spread = abs(line)
            home_adjusted = home_score - spread
            
            if home_adjusted > away_score:
                return BetOutcome.WON if "home" in bet_team.lower() else BetOutcome.LOST
            elif home_adjusted < away_score:
                return BetOutcome.LOST if "home" in bet_team.lower() else BetOutcome.WON
            else:
                return BetOutcome.PUSH
        else:
            # Away team favored
            spread = line
            away_adjusted = away_score - spread
            
            if away_adjusted > home_score:
                return BetOutcome.WON if "away" in bet_team.lower() else BetOutcome.LOST
            elif away_adjusted < home_score:
                return BetOutcome.LOST if "away" in bet_team.lower() else BetOutcome.WON
            else:
                return BetOutcome.PUSH
    
    def _settle_total(self, bet_team: str, line: float, home_score: int, away_score: int) -> BetOutcome:
        """Settle total (Over/Under) bet.
        
        Args:
            bet_team: "Over X" or "Under X"
            line: Total line
            home_score: Home team score
            away_score: Away team score
        
        Returns:
            Outcome enum
        """
        total = home_score + away_score
        
        if "Over" in bet_team:
            if total > line:
                return BetOutcome.WON
            elif total < line:
                return BetOutcome.LOST
            else:
                return BetOutcome.PUSH
        elif "Under" in bet_team:
            if total < line:
                return BetOutcome.WON
            elif total > line:
                return BetOutcome.LOST
            else:
                return BetOutcome.PUSH
        else:
            return BetOutcome.LOST
    
    def _normalize_team(self, team_name: str) -> str:
        """Normalize team name for comparison.
        
        Handles:
        - Lowercasing
        - Removing accents
        - Removing common prefixes/suffixes
        
        Args:
            team_name: Team name to normalize
        
        Returns:
            Normalized team name
        """
        import unicodedata
        
        # Lowercase
        normalized = team_name.lower().strip()
        
        # Remove accents
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Common mappings for team name variations
        mappings = {
            'manchester city': 'man city',
            'manchester united': 'man utd',
            'atletico madrid': 'atletico',
            'real madrid': 'real',
            'paris saint germain': 'psg',
            'paris sg': 'psg',
            'los angeles lakers': 'lakers',
            'golden state warriors': 'warriors',
            'golden state': 'warriors',
            'new york knicks': 'knicks',
            'new york': 'knicks',
            'los angeles clippers': 'clippers',
        }
        
        for key, val in mappings.items():
            if key in normalized:
                normalized = normalized.replace(key, val)
        
        return normalized
    
    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match score (0-1) using token_set ratio.
        
        Args:
            str1: First string
            str2: Second string
        
        Returns:
            Match score from 0.0 to 1.0
        """
        s1 = self._normalize_team(str1)
        s2 = self._normalize_team(str2)
        
        # Use token_set_ratio for better matching of team names with different word orders
        # e.g., "Manchester City" vs "City Manchester"
        score = fuzz.token_set_ratio(s1, s2) / 100.0
        
        return score
    
    def fetch_today_results(self, sport: str = "soccer") -> List[Game]:
        """Fetch today's match results from available APIs.
        
        Args:
            sport: Sport to fetch results for
        
        Returns:
            List of Game objects with scores
        """
        # TODO: Implement actual API calls
        # Options:
        # 1. Flashscore API (if available with auth)
        # 2. ESPN API
        # 3. Nike.sk scraper with scores
        # 4. OddsAPI (if it includes scores)
        
        results = []
        
        # For now, return empty list
        # In production, would fetch from multiple APIs
        
        return results
    
    def fetch_results_for_date(self, date: datetime, sport: str = "soccer") -> List[Game]:
        """Fetch match results for a specific date.
        
        Args:
            date: Date to fetch results for
            sport: Sport to fetch results for
        
        Returns:
            List of Game objects with scores
        """
        # TODO: Implement date-based fetching
        return []
