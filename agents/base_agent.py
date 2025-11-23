"""Base agent class for all betting agents."""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from anthropic import Anthropic
from config.settings import settings


class AgentType(Enum):
    """Types of betting agents."""
    SHARP = "sharp"
    INSIDER = "insider"
    DEGEN = "degen"
    BOOKIE = "bookie"


@dataclass
class Bet:
    """Represents a betting decision."""
    game_id: str
    team: str
    bet_type: str  # moneyline, spread, total
    line: float
    odds: float
    stake: float
    confidence: float  # 0-1
    reasoning: str
    agent_name: str


@dataclass
class Game:
    """Represents a sports game with betting lines."""
    id: str
    home_team: str
    away_team: str
    sport: str
    commence_time: str
    bookmaker: str
    home_odds: float
    away_odds: float
    home_spread: Optional[float] = None
    away_spread: Optional[float] = None
    over_under: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None


class BaseAgent:
    """Base class for all betting agents."""

    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        personality_prompt: str,
        initial_bankroll: float = 1000.0
    ):
        """Initialize agent.

        Args:
            name: Agent's name
            agent_type: Type of agent
            personality_prompt: Custom personality instructions
            initial_bankroll: Starting bankroll for tracking
        """
        self.name = name
        self.agent_type = agent_type
        self.personality_prompt = personality_prompt
        self.bankroll = initial_bankroll
        self.initial_bankroll = initial_bankroll
        self.bet_history: List[Bet] = []
        self.wins = 0
        self.losses = 0

        # Initialize Anthropic client
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def analyze_game(self, game: Game, context: Dict[str, Any]) -> Optional[Bet]:
        """Analyze a game and return a betting decision.

        Args:
            game: Game to analyze
            context: Additional context (other agents' opinions, market data, etc.)

        Returns:
            Bet object if agent wants to bet, None otherwise
        """
        raise NotImplementedError("Subclasses must implement analyze_game")

    def _call_claude(self, system_prompt: str, user_message: str) -> str:
        """Make a call to Claude API.

        Args:
            system_prompt: System instructions
            user_message: User message/query

        Returns:
            Claude's response
        """
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            return message.content[0].text
        except Exception as e:
            return f"Error calling Claude: {str(e)}"

    def debate(self, topic: str, other_opinions: List[str]) -> str:
        """Participate in a debate about a betting decision.

        Args:
            topic: The debate topic (usually a game/bet)
            other_opinions: Opinions from other agents

        Returns:
            Agent's debate response
        """
        system_prompt = f"""You are {self.name}, a betting agent in the Bratislava Betting Syndicate.

{self.personality_prompt}

You're in a debate with other agents about whether to place a bet. Stay in character and argue your position based on your betting philosophy."""

        user_message = f"""Debate topic: {topic}

Other agents' opinions:
{chr(10).join(f'- {opinion}' for opinion in other_opinions)}

What's your take? Be concise but persuasive (2-3 sentences)."""

        return self._call_claude(system_prompt, user_message)

    def update_bankroll(self, amount: float):
        """Update agent's bankroll after bet result.

        Args:
            amount: Amount won (positive) or lost (negative)
        """
        self.bankroll += amount
        if amount > 0:
            self.wins += 1
        else:
            self.losses += 1

    def get_roi(self) -> float:
        """Calculate agent's ROI.

        Returns:
            ROI as percentage
        """
        if self.initial_bankroll == 0:
            return 0.0
        return ((self.bankroll - self.initial_bankroll) / self.initial_bankroll) * 100

    def get_stats(self) -> Dict[str, Any]:
        """Get agent's statistics.

        Returns:
            Dictionary of stats
        """
        total_bets = len(self.bet_history)
        win_rate = (self.wins / total_bets * 100) if total_bets > 0 else 0

        return {
            "name": self.name,
            "type": self.agent_type.value,
            "bankroll": self.bankroll,
            "initial_bankroll": self.initial_bankroll,
            "roi": self.get_roi(),
            "total_bets": total_bets,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": win_rate,
            "profit_loss": self.bankroll - self.initial_bankroll
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.agent_type.value}) - Bankroll: €{self.bankroll:.2f}, ROI: {self.get_roi():.2f}%"
