"""Calculate realistic bet outcomes based on actual odds."""

import math
from typing import Tuple
from dataclasses import dataclass


@dataclass
class BetOutcome:
    """Bet outcome with realistic probability."""
    home_implied_prob: float  # Implied probability from home odds
    away_implied_prob: float  # Implied probability from away odds
    home_win_prob: float      # Actual win probability (adjusted for vig)
    away_win_prob: float      # Actual win probability (adjusted for vig)


class BetProbabilityCalculator:
    """Calculate win probabilities from odds."""

    @staticmethod
    def american_to_decimal(american_odds: float) -> float:
        """Convert American odds to decimal odds."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    @staticmethod
    def decimal_to_american(decimal_odds: float) -> float:
        """Convert decimal odds to American odds."""
        if decimal_odds < 2:
            return -100 / (decimal_odds - 1)
        else:
            return (decimal_odds - 1) * 100

    @staticmethod
    def implied_probability(american_odds: float) -> float:
        """Calculate implied probability from American odds."""
        decimal = BetProbabilityCalculator.american_to_decimal(american_odds)
        return 1 / decimal

    @staticmethod
    def calculate_vig(home_odds: float, away_odds: float) -> float:
        """Calculate vigorish (house edge) from a pair of odds."""
        home_prob = BetProbabilityCalculator.implied_probability(home_odds)
        away_prob = BetProbabilityCalculator.implied_probability(away_odds)
        total_prob = home_prob + away_prob
        
        # Vig is how much the probabilities exceed 100%
        vig = total_prob - 1.0
        return max(0, vig)

    @staticmethod
    def adjust_for_vig(home_implied: float, away_implied: float) -> Tuple[float, float]:
        """Adjust implied probabilities for vigorish (normalize to 100%)."""
        total = home_implied + away_implied
        if total == 0:
            return 0.5, 0.5
        
        home_adjusted = home_implied / total
        away_adjusted = away_implied / total
        return home_adjusted, away_adjusted

    @staticmethod
    def calculate_outcome_probabilities(
        home_odds: float,
        away_odds: float,
        kelly_confidence: float = 1.0
    ) -> BetOutcome:
        """
        Calculate realistic win probabilities from moneyline odds.
        
        Args:
            home_odds: American odds for home team
            away_odds: American odds for away team
            kelly_confidence: Agent's confidence adjustment (0.0-2.0)
                            - 0.5 = low confidence (closer to 50/50)
                            - 1.0 = normal (use implied probabilities)
                            - 2.0 = high confidence (exaggerate edge)
        
        Returns:
            BetOutcome with calculated probabilities
        """
        home_implied = BetProbabilityCalculator.implied_probability(home_odds)
        away_implied = BetProbabilityCalculator.implied_probability(away_odds)
        
        # Normalize for vig
        home_prob, away_prob = BetProbabilityCalculator.adjust_for_vig(home_implied, away_implied)
        
        # Apply confidence adjustment (move towards or away from 50/50)
        # High confidence = exaggerate edge, low confidence = regress to mean
        if kelly_confidence != 1.0:
            base_prob = 0.5
            home_prob = base_prob + (home_prob - base_prob) * kelly_confidence
            away_prob = base_prob + (away_prob - base_prob) * kelly_confidence
            
            # Renormalize
            total = home_prob + away_prob
            home_prob /= total
            away_prob /= total
        
        return BetOutcome(
            home_implied_prob=home_implied,
            away_implied_prob=away_implied,
            home_win_prob=home_prob,
            away_win_prob=away_prob
        )

    @staticmethod
    def should_bet_win(
        home_odds: float,
        away_odds: float,
        betting_team: str,
        agent_confidence: float,
        add_variance: bool = True
    ) -> bool:
        """
        Simulate a bet outcome.
        
        Args:
            home_odds: Home team American odds
            away_odds: Away team American odds
            betting_team: "home" or "away"
            agent_confidence: Agent's confidence in the bet (0.0-1.0)
            add_variance: Add randomness (True) or deterministic (False)
        
        Returns:
            True if bet wins, False if bet loses
        """
        import random
        
        outcome = BetProbabilityCalculator.calculate_outcome_probabilities(
            home_odds,
            away_odds,
            kelly_confidence=agent_confidence
        )
        
        # Get win probability for betting team
        if betting_team.lower() == "home":
            win_prob = outcome.home_win_prob
        else:
            win_prob = outcome.away_win_prob
        
        if add_variance:
            # Add Gaussian noise for realism (±5% variance)
            noise = random.gauss(0, 0.05)
            win_prob = max(0.0, min(1.0, win_prob + noise))
        
        # Simulate outcome
        return random.random() < win_prob

    @staticmethod
    def calculate_expected_value(
        odds: float,
        win_probability: float,
        stake: float
    ) -> float:
        """
        Calculate expected value of a bet.
        
        Args:
            odds: American odds
            win_probability: Probability of winning (0.0-1.0)
            stake: Bet amount
        
        Returns:
            Expected value (in currency units)
        """
        decimal_odds = BetProbabilityCalculator.american_to_decimal(odds)
        win_payoff = stake * (decimal_odds - 1)  # Profit if win
        loss_payoff = -stake  # Loss if lose
        
        ev = (win_probability * win_payoff) + ((1 - win_probability) * loss_payoff)
        return ev

    @staticmethod
    def has_positive_ev(
        odds: float,
        win_probability: float,
        ev_threshold: float = 0.01
    ) -> bool:
        """Check if a bet has positive expected value."""
        ev = BetProbabilityCalculator.calculate_expected_value(odds, win_probability, 1.0)
        return ev > ev_threshold

    @staticmethod
    def calculate_true_odds(
        win_probability: float,
        target_margin: float = 0.05
    ) -> float:
        """
        Calculate fair American odds for a given probability.
        
        Args:
            win_probability: Win probability (0.0-1.0)
            target_margin: Bookmaker margin to add
        
        Returns:
            American odds
        """
        # Adjust probability for margin
        adjusted_prob = win_probability / (1 + target_margin)
        
        # Convert to odds
        decimal = 1 / adjusted_prob
        return BetProbabilityCalculator.decimal_to_american(decimal)
