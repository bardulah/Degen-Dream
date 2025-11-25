"""Agent learning system for confidence weighting based on historical accuracy."""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.orm import Session

from database.schema import AgentSimulationStats, Bet
from monitoring.logger import logger


@dataclass
class AgentStats:
    """Statistics for an agent's performance."""
    name: str
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_confidence: float = 0.0
    confidence_accuracy: float = 0.0  # Calibration: does 80% confidence = 80% win rate?
    recent_performance: float = 0.0  # Win rate on last N bets
    roi: float = 0.0


class AgentLearningSystem:
    """Learns from agent performance and adjusts confidence weighting."""

    def __init__(self, db: Session):
        """Initialize learning system.
        
        Args:
            db: Database session
        """
        self.db = db
        self.performance_cache: Dict[str, AgentStats] = {}
        self.last_update: Dict[str, datetime] = {}

    def update_agent_stats(
        self,
        agent_name: str,
        simulation_id: str,
        bets: List[Dict]
    ):
        """Update agent statistics after simulation.
        
        Args:
            agent_name: Name of agent
            simulation_id: Simulation ID
            bets: List of bet outcomes from agent
        """
        if not bets:
            return
        
        # Calculate basic stats
        wins = sum(1 for b in bets if b.get("result") == "win")
        losses = sum(1 for b in bets if b.get("result") == "loss")
        total = wins + losses
        
        if total == 0:
            return
        
        win_rate = wins / total
        avg_confidence = np.mean([b.get("confidence", 0.5) for b in bets])
        
        # Calculate confidence calibration
        confidence_calibration = self._calculate_confidence_calibration(bets)
        
        # Store or update stats
        stats = self.performance_cache.get(agent_name)
        if stats is None:
            stats = AgentStats(name=agent_name)
        
        stats.total_bets += total
        stats.wins += wins
        stats.losses += losses
        stats.win_rate = stats.wins / stats.total_bets if stats.total_bets > 0 else 0.0
        stats.avg_confidence = avg_confidence
        stats.confidence_accuracy = confidence_calibration
        stats.recent_performance = win_rate
        
        self.performance_cache[agent_name] = stats
        self.last_update[agent_name] = datetime.utcnow()
        
        logger.log_agent_performance(
            agent_name=agent_name,
            win_rate=stats.win_rate,
            total_bets=stats.total_bets,
            confidence_accuracy=confidence_calibration
        )

    def get_confidence_weight(self, agent_name: str) -> float:
        """Get confidence weight adjustment for agent.
        
        A well-calibrated agent (80% confidence = 80% win rate) gets weight ~1.0
        An overconfident agent gets weight < 1.0
        An underconfident agent gets weight > 1.0
        
        Args:
            agent_name: Agent name
            
        Returns:
            Confidence weight multiplier (0.5 - 2.0)
        """
        stats = self.performance_cache.get(agent_name)
        if stats is None or stats.total_bets < 10:
            # Not enough data, use neutral weight
            return 1.0
        
        # Compare stated confidence to actual win rate
        confidence_error = stats.confidence_accuracy - stats.avg_confidence
        
        # Weight = 1.0 + error/100, clamped to [0.5, 2.0]
        weight = 1.0 + (confidence_error / 100.0)
        weight = max(0.5, min(2.0, weight))
        
        return weight

    def adjust_agent_confidence(
        self,
        agent_name: str,
        original_confidence: float
    ) -> float:
        """Adjust agent's stated confidence based on historical accuracy.
        
        Args:
            agent_name: Agent name
            original_confidence: Originally stated confidence (0-1)
            
        Returns:
            Adjusted confidence (0-1)
        """
        weight = self.get_confidence_weight(agent_name)
        adjusted = original_confidence * weight
        
        # Clamp to valid range
        return max(0.01, min(0.99, adjusted))

    def get_agent_stats(self, agent_name: str) -> Optional[AgentStats]:
        """Get current stats for an agent.
        
        Args:
            agent_name: Agent name
            
        Returns:
            AgentStats or None if no data
        """
        return self.performance_cache.get(agent_name)

    def get_all_agent_stats(self) -> Dict[str, AgentStats]:
        """Get stats for all agents.
        
        Returns:
            Dict of agent_name -> AgentStats
        """
        return self.performance_cache.copy()

    def get_top_agents(self, n: int = 5) -> List[Tuple[str, AgentStats]]:
        """Get top N performing agents.
        
        Args:
            n: Number of agents to return
            
        Returns:
            List of (agent_name, stats) sorted by ROI
        """
        agents = sorted(
            self.performance_cache.items(),
            key=lambda x: x[1].roi,
            reverse=True
        )
        return agents[:n]

    def get_best_calibrated_agents(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get agents with best confidence calibration.
        
        Args:
            n: Number of agents to return
            
        Returns:
            List of (agent_name, calibration_score) sorted by calibration
        """
        agents = sorted(
            self.performance_cache.items(),
            key=lambda x: abs(x[1].confidence_accuracy - x[1].avg_confidence)
        )
        return agents[:n]

    def reset_stats(self):
        """Reset all statistics."""
        self.performance_cache.clear()
        self.last_update.clear()

    def _calculate_confidence_calibration(self, bets: List[Dict]) -> float:
        """Calculate how well agent's confidence matches actual outcomes.
        
        A perfectly calibrated agent has confidence values that match win rates.
        E.g., 80% confidence bets should win ~80% of the time.
        
        Args:
            bets: List of bets with confidence and result
            
        Returns:
            Calibration score (0-1), 1.0 = perfect calibration
        """
        if not bets or len(bets) < 5:
            return 0.5  # Neutral if insufficient data
        
        # Group bets by confidence bins (e.g., 50-60%, 60-70%, etc.)
        bins = {}
        bin_size = 0.1  # 10% confidence bins
        
        for bet in bets:
            confidence = bet.get("confidence", 0.5)
            result = bet.get("result") == "win"
            
            # Round to nearest bin
            bin_key = round(confidence / bin_size) * bin_size
            if bin_key not in bins:
                bins[bin_key] = {"wins": 0, "total": 0}
            
            bins[bin_key]["total"] += 1
            if result:
                bins[bin_key]["wins"] += 1
        
        # Calculate calibration error
        errors = []
        for bin_key, data in bins.items():
            if data["total"] >= 2:  # Need at least 2 bets per bin
                actual_win_rate = data["wins"] / data["total"]
                expected_win_rate = bin_key
                error = abs(actual_win_rate - expected_win_rate)
                errors.append(error)
        
        if not errors:
            return 0.5
        
        # Return inverse of mean absolute error (higher = better calibrated)
        mean_error = np.mean(errors)
        calibration = 1.0 - min(mean_error, 0.5)  # Cap at 0.5 (0.0 means max error)
        
        return calibration

    def export_agent_rankings(self) -> List[Dict]:
        """Export agent rankings as dictionaries.
        
        Returns:
            List of agent stats dicts sorted by ROI
        """
        agents = sorted(
            self.performance_cache.items(),
            key=lambda x: x[1].roi,
            reverse=True
        )
        
        return [
            {
                "rank": i + 1,
                "name": name,
                "type": "custom",  # TODO: Get actual type
                "roi": stats.roi,
                "win_rate": f"{stats.win_rate:.1%}",
                "total_bets": stats.total_bets,
                "confidence_accuracy": f"{stats.confidence_accuracy:.2f}",
                "recent_performance": f"{stats.recent_performance:.1%}"
            }
            for i, (name, stats) in enumerate(agents)
        ]


class ConfidenceAdjustmentFilter:
    """Applies confidence adjustments based on agent learning."""

    def __init__(self, learning_system: AgentLearningSystem):
        """Initialize filter.
        
        Args:
            learning_system: AgentLearningSystem instance
        """
        self.learning = learning_system

    def adjust_bet_confidence(
        self,
        agent_name: str,
        bet_confidence: float
    ) -> float:
        """Adjust a bet's confidence based on agent history.
        
        Args:
            agent_name: Agent making the bet
            bet_confidence: Original confidence (0-1)
            
        Returns:
            Adjusted confidence (0-1)
        """
        stats = self.learning.get_agent_stats(agent_name)
        
        if stats is None or stats.total_bets < 10:
            # Not enough data
            return bet_confidence
        
        # Adjust based on calibration
        weight = self.learning.get_confidence_weight(agent_name)
        return self.learning.adjust_agent_confidence(agent_name, bet_confidence)

    def should_accept_bet(
        self,
        agent_name: str,
        bet_confidence: float,
        min_threshold: float = 0.55
    ) -> bool:
        """Determine if bet should be accepted based on agent history.
        
        Args:
            agent_name: Agent making bet
            bet_confidence: Original confidence
            min_threshold: Minimum confidence required
            
        Returns:
            True if bet should be placed
        """
        adjusted = self.adjust_bet_confidence(agent_name, bet_confidence)
        return adjusted >= min_threshold
