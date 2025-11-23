"""Kelly Criterion implementation for optimal bet sizing."""

from typing import Optional
import math


class KellyCalculator:
    """Kelly Criterion calculator for optimal bet sizing."""

    def __init__(self, fraction: float = 0.25):
        """Initialize Kelly calculator.

        Args:
            fraction: Fraction of Kelly to use (0.25 = quarter-Kelly, safer)
        """
        self.fraction = fraction

    def calculate_stake(
        self,
        bankroll: float,
        probability: float,
        odds: float,
        max_stake_pct: float = 0.10
    ) -> float:
        """Calculate optimal stake using Kelly Criterion.

        Args:
            bankroll: Current bankroll
            probability: Estimated win probability (0-1)
            odds: Decimal odds
            max_stake_pct: Maximum stake as percentage of bankroll

        Returns:
            Recommended stake amount
        """
        # Kelly formula: (bp - q) / b
        # where b = odds - 1, p = probability, q = 1 - p

        b = odds - 1  # Net odds
        p = probability
        q = 1 - p

        # Full Kelly percentage
        kelly_pct = (b * p - q) / b

        # Apply fraction (conservative)
        kelly_pct = kelly_pct * self.fraction

        # Ensure non-negative
        kelly_pct = max(0, kelly_pct)

        # Cap at max stake percentage
        kelly_pct = min(kelly_pct, max_stake_pct)

        # Calculate stake
        stake = bankroll * kelly_pct

        return round(stake, 2)

    def calculate_edge(self, true_probability: float, offered_odds: float) -> float:
        """Calculate betting edge.

        Args:
            true_probability: Your estimated true probability
            offered_odds: Bookmaker's decimal odds

        Returns:
            Edge as decimal (0.05 = 5% edge)
        """
        implied_probability = 1 / offered_odds
        edge = true_probability - implied_probability

        return edge

    def kelly_percentage(
        self,
        probability: float,
        odds: float
    ) -> float:
        """Calculate Kelly percentage (for analysis).

        Args:
            probability: Win probability
            odds: Decimal odds

        Returns:
            Kelly percentage (can be > 1.0 for very +EV bets)
        """
        b = odds - 1
        p = probability
        q = 1 - p

        kelly_pct = (b * p - q) / b

        return max(0, kelly_pct)

    def expected_value(
        self,
        stake: float,
        probability: float,
        odds: float
    ) -> float:
        """Calculate expected value of a bet.

        Args:
            stake: Bet stake
            probability: Win probability
            odds: Decimal odds

        Returns:
            Expected value (profit/loss)
        """
        win_amount = stake * (odds - 1)
        lose_amount = -stake

        ev = (probability * win_amount) + ((1 - probability) * lose_amount)

        return ev

    def growth_rate(
        self,
        stake_pct: float,
        probability: float,
        odds: float
    ) -> float:
        """Calculate expected bankroll growth rate.

        Args:
            stake_pct: Stake as percentage of bankroll
            probability: Win probability
            odds: Decimal odds

        Returns:
            Expected log growth rate
        """
        p = probability
        q = 1 - p

        if stake_pct >= 1.0:
            return float('-inf')  # Risking entire bankroll

        # Log growth formula
        try:
            growth = (
                p * math.log(1 + stake_pct * (odds - 1)) +
                q * math.log(1 - stake_pct)
            )
            return growth
        except ValueError:
            return float('-inf')

    def simulate_outcomes(
        self,
        initial_bankroll: float,
        bets: int,
        probability: float,
        odds: float,
        stake_method: str = "kelly"
    ) -> float:
        """Simulate expected bankroll after N bets.

        Args:
            initial_bankroll: Starting bankroll
            bets: Number of bets
            probability: Win probability per bet
            odds: Decimal odds
            stake_method: "kelly", "flat", or "martingale"

        Returns:
            Expected final bankroll
        """
        bankroll = initial_bankroll

        for _ in range(bets):
            if stake_method == "kelly":
                stake_pct = self.kelly_percentage(probability, odds) * self.fraction
                stake = bankroll * min(stake_pct, 0.10)
            elif stake_method == "flat":
                stake = initial_bankroll * 0.02  # Flat 2%
            else:
                stake = bankroll * 0.02

            # Expected outcome (not random, just mathematical expectation)
            win_prob = probability
            expected_return = (
                win_prob * (stake * odds) +
                (1 - win_prob) * 0  # Lose stake
            ) - stake

            bankroll += expected_return

            # Stop if bankroll depleted
            if bankroll <= 0:
                return 0

        return bankroll
