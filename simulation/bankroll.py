"""Bankroll management for the betting syndicate."""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from agents.base_agent import Bet


@dataclass
class BankrollSnapshot:
    """Snapshot of bankroll at a point in time."""
    timestamp: datetime
    total_bankroll: float
    bets_placed: int
    wins: int
    losses: int
    roi: float
    biggest_win: float = 0
    biggest_loss: float = 0


class BankrollManager:
    """Manages bankroll across all agents and tracks performance."""

    def __init__(self, initial_bankroll: float):
        """Initialize bankroll manager.

        Args:
            initial_bankroll: Starting bankroll for the syndicate
        """
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.bets_placed: List[Bet] = []
        self.settled_bets: List[tuple[Bet, bool, float]] = []  # (bet, won, profit/loss)
        self.snapshots: List[BankrollSnapshot] = []

        self.total_wagered = 0
        self.total_won = 0
        self.total_lost = 0

    def place_bet(self, bet: Bet) -> bool:
        """Place a bet and deduct from bankroll.

        Args:
            bet: Bet to place

        Returns:
            True if bet was placed, False if insufficient funds
        """
        if bet.stake > self.current_bankroll:
            print(f"❌ Insufficient funds for {bet.agent_name}'s bet: €{bet.stake:.2f}")
            return False

        self.bets_placed.append(bet)
        self.current_bankroll -= bet.stake
        self.total_wagered += bet.stake

        return True

    def settle_bet(self, bet: Bet, won: bool) -> float:
        """Settle a bet and update bankroll.

        Args:
            bet: Bet to settle
            won: Whether the bet won

        Returns:
            Profit or loss amount
        """
        if won:
            # Win: get stake back plus profit
            profit = bet.stake * (bet.odds - 1)
            total_return = bet.stake + profit
            self.current_bankroll += total_return
            self.total_won += profit

            self.settled_bets.append((bet, True, profit))
            return profit
        else:
            # Loss: lose stake (already deducted)
            loss = -bet.stake
            self.total_lost += bet.stake

            self.settled_bets.append((bet, False, loss))
            return loss

    def take_snapshot(self):
        """Take a snapshot of current bankroll state."""
        wins = sum(1 for _, won, _ in self.settled_bets if won)
        losses = sum(1 for _, won, _ in self.settled_bets if not won)

        profits = [p for _, won, p in self.settled_bets if won]
        losses_list = [p for _, won, p in self.settled_bets if not won]

        snapshot = BankrollSnapshot(
            timestamp=datetime.now(),
            total_bankroll=self.current_bankroll,
            bets_placed=len(self.bets_placed),
            wins=wins,
            losses=losses,
            roi=self.get_roi(),
            biggest_win=max(profits) if profits else 0,
            biggest_loss=min(losses_list) if losses_list else 0
        )

        self.snapshots.append(snapshot)

    def get_roi(self) -> float:
        """Calculate current ROI.

        Returns:
            ROI as percentage
        """
        if self.initial_bankroll == 0:
            return 0

        return ((self.current_bankroll - self.initial_bankroll) / self.initial_bankroll) * 100

    def get_profit_loss(self) -> float:
        """Get total profit/loss.

        Returns:
            Profit (positive) or loss (negative)
        """
        return self.current_bankroll - self.initial_bankroll

    def get_win_rate(self) -> float:
        """Calculate win rate.

        Returns:
            Win rate as percentage
        """
        if not self.settled_bets:
            return 0

        wins = sum(1 for _, won, _ in self.settled_bets if won)
        return (wins / len(self.settled_bets)) * 100

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics.

        Returns:
            Dictionary of statistics
        """
        wins = sum(1 for _, won, _ in self.settled_bets if won)
        losses = sum(1 for _, won, _ in self.settled_bets if not won)

        return {
            "initial_bankroll": self.initial_bankroll,
            "current_bankroll": self.current_bankroll,
            "profit_loss": self.get_profit_loss(),
            "roi": self.get_roi(),
            "total_bets": len(self.settled_bets),
            "wins": wins,
            "losses": losses,
            "win_rate": self.get_win_rate(),
            "total_wagered": self.total_wagered,
            "average_bet_size": self.total_wagered / len(self.bets_placed) if self.bets_placed else 0,
            "pending_bets": len(self.bets_placed) - len(self.settled_bets)
        }

    def get_performance_over_time(self) -> List[Dict[str, Any]]:
        """Get bankroll performance over time.

        Returns:
            List of snapshots as dicts
        """
        return [
            {
                "timestamp": snap.timestamp.isoformat(),
                "bankroll": snap.total_bankroll,
                "roi": snap.roi,
                "bets": snap.bets_placed,
                "wins": snap.wins,
                "losses": snap.losses
            }
            for snap in self.snapshots
        ]

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Bankroll: €{self.current_bankroll:.2f} "
            f"(ROI: {self.get_roi():.2f}%, "
            f"Win Rate: {self.get_win_rate():.1f}%)"
        )
