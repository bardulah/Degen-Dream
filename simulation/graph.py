"""LangGraph orchestration for multi-agent betting syndicate."""

from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
import random
from datetime import datetime

from agents.base_agent import Game, Bet
from agents.sharp_agent import SharpAgent
from agents.insider_agent import InsiderAgent
from agents.degen_agent import DegenAgent
from agents.bookie_agent import BookieAgent
from simulation.bankroll import BankrollManager
from simulation.kelly import KellyCalculator
from config.settings import settings


class SyndicateState(TypedDict):
    """State for the syndicate graph."""
    game: Game
    agent_bets: List[Bet]
    debate_history: List[str]
    consensus_bet: Optional[Bet]
    market_context: Dict[str, Any]


class SyndicateGraph:
    """LangGraph-based multi-agent betting syndicate."""

    def __init__(
        self,
        agents: Optional[List] = None,
        bankroll_manager: Optional[BankrollManager] = None
    ):
        """Initialize syndicate graph.

        Args:
            agents: List of agents (if None, creates default 10)
            bankroll_manager: Bankroll manager instance
        """
        self.agents = agents or self._create_default_agents()
        self.bankroll_manager = bankroll_manager or BankrollManager(
            settings.STARTING_BANKROLL
        )
        self.kelly_calculator = KellyCalculator(fraction=settings.KELLY_FRACTION)

        # Build the graph
        self.graph = self._build_graph()

    def _create_default_agents(self) -> List:
        """Create the default 10 agents.

        Returns:
            List of agent instances
        """
        agents = []

        # 3 Sharps
        for name in settings.AGENT_NAMES["sharps"]:
            agent = SharpAgent(
                name=name,
                personality_prompt=settings.AGENT_PROMPTS[name],
                initial_bankroll=settings.STARTING_BANKROLL / 10
            )
            agents.append(agent)

        # 2 Insiders
        for name in settings.AGENT_NAMES["insiders"]:
            agent = InsiderAgent(
                name=name,
                personality_prompt=settings.AGENT_PROMPTS[name],
                initial_bankroll=settings.STARTING_BANKROLL / 10
            )
            agents.append(agent)

        # 3 Degens
        for name in settings.AGENT_NAMES["degens"]:
            agent = DegenAgent(
                name=name,
                personality_prompt=settings.AGENT_PROMPTS[name],
                initial_bankroll=settings.STARTING_BANKROLL / 10
            )
            agents.append(agent)

        # 2 Bookies
        for name in settings.AGENT_NAMES["bookies"]:
            agent = BookieAgent(
                name=name,
                personality_prompt=settings.AGENT_PROMPTS[name],
                initial_bankroll=settings.STARTING_BANKROLL / 10
            )
            agents.append(agent)

        return agents

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(SyndicateState)

        # Define nodes
        workflow.add_node("gather_proposals", self._gather_proposals)
        workflow.add_node("debate", self._debate)
        workflow.add_node("vote", self._vote)
        workflow.add_node("place_bet", self._place_bet)

        # Define edges
        workflow.set_entry_point("gather_proposals")
        workflow.add_edge("gather_proposals", "debate")
        workflow.add_edge("debate", "vote")
        workflow.add_edge("vote", "place_bet")
        workflow.add_edge("place_bet", END)

        return workflow.compile()

    def _gather_proposals(self, state: SyndicateState) -> SyndicateState:
        """Gather betting proposals from all agents.

        Args:
            state: Current state

        Returns:
            Updated state with agent bets
        """
        game = state["game"]
        context = state.get("market_context", {})

        agent_bets = []

        print(f"\n🎰 Analyzing: {game.away_team} @ {game.home_team}")
        print("=" * 60)

        for agent in self.agents:
            bet = agent.analyze_game(game, context)
            if bet:
                agent_bets.append(bet)
                print(f"✅ {agent.name} ({agent.agent_type.value}): {bet.bet_type} on {bet.team}")
                print(f"   Stake: €{bet.stake:.2f} | Confidence: {bet.confidence:.0%}")
                print(f"   Reasoning: {bet.reasoning}\n")
            else:
                print(f"❌ {agent.name} ({agent.agent_type.value}): Pass\n")

        state["agent_bets"] = agent_bets
        return state

    def _debate(self, state: SyndicateState) -> SyndicateState:
        """Agents debate their positions.

        Args:
            state: Current state

        Returns:
            Updated state with debate history
        """
        game = state["game"]
        agent_bets = state["agent_bets"]

        if not agent_bets:
            print("No bets proposed, skipping debate.\n")
            state["debate_history"] = []
            return state

        print("\n💬 DEBATE PHASE")
        print("=" * 60)

        debate_topic = f"{game.away_team} @ {game.home_team}"
        debate_history = []

        # Get opinions from agents who made bets
        opinions = [
            f"{bet.agent_name}: {bet.reasoning}"
            for bet in agent_bets
        ]

        # Let each agent respond
        for agent in self.agents[:5]:  # Limit debate to avoid token costs
            response = agent.debate(debate_topic, opinions)
            debate_history.append(f"{agent.name}: {response}")
            print(f"🗣️  {agent.name}: {response}\n")

        state["debate_history"] = debate_history
        return state

    def _vote(self, state: SyndicateState) -> SyndicateState:
        """Vote on which bet to place (consensus building).

        Args:
            state: Current state

        Returns:
            Updated state with consensus bet
        """
        agent_bets = state["agent_bets"]

        if not agent_bets:
            state["consensus_bet"] = None
            return state

        print("\n🗳️  VOTING PHASE")
        print("=" * 60)

        # Simple voting: weighted by confidence
        # In production, this could be more sophisticated
        best_bet = max(agent_bets, key=lambda b: b.confidence)

        print(f"✅ CONSENSUS: {best_bet.agent_name}'s bet on {best_bet.team}")
        print(f"   Bet Type: {best_bet.bet_type}")
        print(f"   Stake: €{best_bet.stake:.2f}")
        print(f"   Confidence: {best_bet.confidence:.0%}\n")

        state["consensus_bet"] = best_bet
        return state

    def _place_bet(self, state: SyndicateState) -> SyndicateState:
        """Place the consensus bet.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        consensus_bet = state["consensus_bet"]

        if not consensus_bet:
            print("⚠️  No consensus reached, no bet placed.\n")
            return state

        # Place bet through bankroll manager
        placed = self.bankroll_manager.place_bet(consensus_bet)

        if placed:
            print(f"✅ BET PLACED: €{consensus_bet.stake:.2f} on {consensus_bet.team}")
            print(f"   Current Bankroll: €{self.bankroll_manager.current_bankroll:.2f}\n")
        else:
            print(f"❌ INSUFFICIENT FUNDS to place bet\n")

        return state

    def analyze_game(self, game: Game, market_context: Dict[str, Any] = None) -> Optional[Bet]:
        """Run the full multi-agent workflow on a game.

        Args:
            game: Game to analyze
            market_context: Additional market data

        Returns:
            Consensus bet if reached
        """
        initial_state: SyndicateState = {
            "game": game,
            "agent_bets": [],
            "debate_history": [],
            "consensus_bet": None,
            "market_context": market_context or {}
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        return final_state["consensus_bet"]

    def get_agent_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all agents.

        Returns:
            List of agent stats
        """
        return [agent.get_stats() for agent in self.agents]


def run_simulation(
    games: List[Game],
    num_games: int = 100,
    starting_bankroll: float = 10000
) -> Dict[str, Any]:
    """Run a full betting simulation.

    Args:
        games: List of games to bet on
        num_games: Number of games to simulate
        starting_bankroll: Starting bankroll

    Returns:
        Simulation results
    """
    print("\n" + "=" * 70)
    print("🎰 BRATISLAVA BETTING SYNDICATE - SIMULATION START 🎰")
    print("=" * 70)

    syndicate = SyndicateGraph()
    bankroll_manager = syndicate.bankroll_manager

    results = []
    games_analyzed = 0

    # Repeat games if we don't have enough
    game_pool = games * (num_games // len(games) + 1)

    for i, game in enumerate(game_pool[:num_games]):
        print(f"\n📊 GAME {i + 1}/{num_games}")

        # Add market context
        market_context = {
            "public_betting": {
                "home": random.uniform(40, 80),
                "away": random.uniform(20, 60)
            },
            "line_movements": f"Opened at {game.home_odds}, moved to {game.home_odds + random.uniform(-10, 10)}"
        }

        # Analyze game
        consensus_bet = syndicate.analyze_game(game, market_context)

        if consensus_bet:
            # Simulate outcome (random for demo, would use real results in production)
            won = random.random() < consensus_bet.confidence

            # Settle bet
            profit_loss = bankroll_manager.settle_bet(consensus_bet, won)

            result_emoji = "✅ WIN" if won else "❌ LOSS"
            print(f"{result_emoji}: {profit_loss:+.2f} EUR")

            results.append({
                "game": f"{game.away_team} @ {game.home_team}",
                "bet": consensus_bet.team,
                "stake": consensus_bet.stake,
                "won": won,
                "profit_loss": profit_loss
            })

        bankroll_manager.take_snapshot()
        games_analyzed += 1

        # Stop if bankroll depleted
        if bankroll_manager.current_bankroll <= 0:
            print("\n💀 BANKROLL DEPLETED - Simulation ended early")
            break

    # Final statistics
    print("\n" + "=" * 70)
    print("📊 SIMULATION COMPLETE")
    print("=" * 70)

    stats = bankroll_manager.get_statistics()
    agent_stats = syndicate.get_agent_stats()

    print(f"\n💰 Final Bankroll: €{stats['current_bankroll']:.2f}")
    print(f"📈 ROI: {stats['roi']:+.2f}%")
    print(f"🎯 Win Rate: {stats['win_rate']:.1f}%")
    print(f"🎲 Total Bets: {stats['total_bets']}")
    print(f"💵 Total Wagered: €{stats['total_wagered']:.2f}")

    return {
        "stats": stats,
        "agent_stats": agent_stats,
        "results": results,
        "performance": bankroll_manager.get_performance_over_time()
    }
