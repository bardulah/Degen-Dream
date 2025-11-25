"""LangGraph orchestration for multi-agent betting syndicate."""

import uuid
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
import random
from datetime import datetime
from sqlalchemy.orm import Session

from agents.base_agent import Game, Bet
from agents.sharp_agent import SharpAgent
from agents.insider_agent import InsiderAgent
from agents.degen_agent import DegenAgent
from agents.bookie_agent import BookieAgent
from simulation.bankroll import BankrollManager
from simulation.kelly import KellyCalculator
from simulation.bet_probability import BetProbabilityCalculator
from config.settings import settings
from monitoring.logger import logger
from database.simulation_store import SimulationStore
from database.schema import Simulation


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
        bankroll_manager: Optional[BankrollManager] = None,
        db: Optional[Session] = None,
        simulation_id: Optional[str] = None
    ):
        """Initialize syndicate graph.

        Args:
            agents: List of agents (if None, creates default 10)
            bankroll_manager: Bankroll manager instance
            db: Database session (optional)
            simulation_id: Simulation ID (optional)
        """
        self.agents = agents or self._create_default_agents()
        self.bankroll_manager = bankroll_manager or BankrollManager(
            settings.STARTING_BANKROLL
        )
        self.kelly_calculator = KellyCalculator(fraction=settings.KELLY_FRACTION)
        self.db = db
        self.simulation_id = simulation_id

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

        if hasattr(self, 'monitor') and self.monitor:
            self.monitor.log_event("INFO", f"Analyzing: {game.away_team} @ {game.home_team}")
        else:
            print(f"\n🎰 Analyzing: {game.away_team} @ {game.home_team}")
            print("=" * 60)

        for agent in self.agents:
            bet = agent.analyze_game(game, context)
            
            # Format response for monitor
            if bet:
                response = f"I'm betting on {bet.team} ({bet.bet_type}). {bet.reasoning}"
                decision = {
                    "bet_type": bet.bet_type,
                    "stake": bet.stake,
                    "confidence": bet.confidence,
                    "odds": bet.odds
                }
            else:
                response = "Pass. No value found."
                decision = None

            # Send to monitor if available
            if hasattr(self, 'monitor') and self.monitor:
                self.monitor.show_agent_response(
                    agent_name=agent.name,
                    agent_type=agent.agent_type.value,
                    response=response,
                    decision=decision
                )

            if bet:
                agent_bets.append(bet)
                if not (hasattr(self, 'monitor') and self.monitor):
                    print(f"✅ {agent.name} ({agent.agent_type.value}): {bet.bet_type} on {bet.team}")
                    print(f"   Stake: €{bet.stake:.2f} | Confidence: {bet.confidence:.0%}")
                    print(f"   Reasoning: {bet.reasoning}\n")
            else:
                if not (hasattr(self, 'monitor') and self.monitor):
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
            if not (hasattr(self, 'monitor') and self.monitor):
                print("No bets proposed, skipping debate.\n")
            state["debate_history"] = []
            return state

        if not (hasattr(self, 'monitor') and self.monitor):
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
            
            if hasattr(self, 'monitor') and self.monitor:
                # Update thought with debate response
                self.monitor.show_agent_response(
                    agent_name=agent.name,
                    agent_type=agent.agent_type.value,
                    response=f"[DEBATE] {response}"
                )
            else:
                print(f"🗣️  {agent.name}: {response}\n")

        state["debate_history"] = debate_history
        return state

    def _vote(self, state: SyndicateState) -> SyndicateState:
        """Vote on which bet to place (consensus building).
        
        Everyone gets an equal vote. The Oracle decides based on:
        - Agent agreement (which team gets most votes)
        - Stake size (more aggressive = more conviction)
        - Confidence (agent belief level)

        Args:
            state: Current state

        Returns:
            Updated state with consensus bet
        """
        agent_bets = state["agent_bets"]

        if not agent_bets:
            state["consensus_bet"] = None
            return state

        if not (hasattr(self, 'monitor') and self.monitor):
            print("\n🗳️  VOTING PHASE")
            print("=" * 60)

        # Democratic voting: each agent gets 1 vote
        best_bet = self._oracle_decides(agent_bets)

        if not (hasattr(self, 'monitor') and self.monitor):
            print(f"✅ CONSENSUS: {best_bet.agent_name}'s bet on {best_bet.team}")
            print(f"   Bet Type: {best_bet.bet_type}")
            print(f"   Stake: €{best_bet.stake:.2f}")
            print(f"   Confidence: {best_bet.confidence:.0%}\n")

        state["consensus_bet"] = best_bet
        return state

    def _oracle_decides(self, agent_bets: List[Bet]) -> Bet:
        """Oracle picks the winning bet from all agent votes.
        
        Algorithm:
        1. Count votes for each team/outcome
        2. The team with most votes wins (democratic)
        3. Among bets on that team, pick the one with highest combined score
           (stake + confidence)
        
        Args:
            agent_bets: All bets proposed by agents
            
        Returns:
            The oracle's chosen bet
        """
        # Count votes by team
        team_votes = {}
        team_bets = {}  # Track which bets vote for each team
        
        for bet in agent_bets:
            team = bet.team
            if team not in team_votes:
                team_votes[team] = 0
                team_bets[team] = []
            
            team_votes[team] += 1
            team_bets[team].append(bet)
        
        # Find the team with most votes
        winning_team = max(team_votes, key=team_votes.get)
        votes_for_winner = team_votes[winning_team]
        winning_bets = team_bets[winning_team]
        
        # Among winning team's bets, pick by oracle score
        # Oracle score = stake + confidence (both matter equally)
        best_bet = max(
            winning_bets,
            key=lambda b: (b.stake + b.confidence)
        )
        
        if not (hasattr(self, 'monitor') and self.monitor):
            print(f"\n🔮 ORACLE'S WISDOM:")
            print(f"   Votes for {winning_team}: {votes_for_winner}/{len(agent_bets)}")
            print(f"   Oracle chooses: {best_bet.agent_name}'s conviction")
        
        return best_bet

    def _place_bet(self, state: SyndicateState) -> SyndicateState:
        """Place the consensus bet.

        Args:
            state: Current state

        Returns:
            Updated state
        """
        consensus_bet = state["consensus_bet"]
        game = state["game"]

        if not consensus_bet:
            print("⚠️  No consensus reached, no bet placed.\n")
            return state

        # Place bet through bankroll manager
        placed = self.bankroll_manager.place_bet(consensus_bet)

        if placed:
            print(f"✅ BET PLACED: €{consensus_bet.stake:.2f} on {consensus_bet.team}")
            print(f"   Current Bankroll: €{self.bankroll_manager.current_bankroll:.2f}\n")
            
            # Save to DB if available
            if self.db and self.simulation_id:
                bet_id = SimulationStore.save_bet(
                    db=self.db,
                    simulation_id=self.simulation_id,
                    agent_name=consensus_bet.agent_name,
                    game_home_team=game.home_team,
                    game_away_team=game.away_team,
                    sport=game.sport if hasattr(game, 'sport') else "unknown",
                    bet_team=consensus_bet.team,
                    bet_type=consensus_bet.bet_type,
                    line=0.0,  # TODO: Capture line if available
                    odds=consensus_bet.odds,
                    stake=consensus_bet.stake,
                    confidence=consensus_bet.confidence,
                    reasoning=consensus_bet.reasoning,
                    outcome="pending"
                )
                if bet_id:
                    consensus_bet.id = bet_id  # Monkey-patch ID onto bet object
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
    starting_bankroll: float = 10000,
    monitor: Optional[Any] = None,
    db: Optional[Session] = None,
    user_id: Optional[str] = None,
    simulation_id: Optional[str] = None,
    sport: str = "unknown",
    use_live_data: bool = False
) -> Dict[str, Any]:
    """Run a full betting simulation.

    Args:
        games: List of games to bet on
        num_games: Number of games to simulate
        starting_bankroll: Starting bankroll
        monitor: Optional AgentMonitor for real-time visualization
        db: Database session
        user_id: User ID
        simulation_id: Simulation ID
        sport: Sport being simulated
        use_live_data: Whether live data was used

    Returns:
        Simulation results
    """
    start_time = datetime.utcnow()
    
    if not monitor:
        print("\n" + "=" * 70)
        print("🎰 BRATISLAVA BETTING SYNDICATE - SIMULATION START 🎰")
        print("=" * 70)

    syndicate = SyndicateGraph(
        bankroll_manager=None, # Use default
        db=db,
        simulation_id=simulation_id
    )
    # Override bankroll if needed (constructor creates one with default starting bankroll from settings, 
    # but we want to use the passed starting_bankroll)
    syndicate.bankroll_manager = BankrollManager(starting_bankroll)
    
    syndicate.monitor = monitor  # Pass monitor to syndicate
    bankroll_manager = syndicate.bankroll_manager
    
    # Initialize Search Client
    try:
        from data.gemini_search import GeminiSearchClient
        search_client = GeminiSearchClient()
        search_enabled = True
        if monitor:
            monitor.log_event("INFO", "Gemini Search Grounding enabled")
        else:
            print("🔍 Gemini Search Grounding enabled")
    except Exception as e:
        search_enabled = False
        if monitor:
            monitor.show_warning(f"Gemini Search disabled: {e}")

    results = []
    games_analyzed = 0

    # Repeat games if we don't have enough
    game_pool = games * (num_games // len(games) + 1)

    for i, game in enumerate(game_pool[:num_games]):
        if monitor:
            monitor.show_separator()
            monitor.log_event("INFO", f"Game {i + 1}/{num_games}")
            monitor.show_game(game)
        else:
            print(f"\n📊 GAME {i + 1}/{num_games}")

        # Add market context
        market_context = {
            "public_betting": {
                "home": random.uniform(40, 80),
                "away": random.uniform(20, 60)
            },
            "line_movements": f"Opened at {game.home_odds}, moved to {game.home_odds + random.uniform(-10, 10)}"
        }
        
        # Fetch Real-Time Context if enabled
        if search_enabled:
            if monitor:
                monitor.log_event("INFO", f"Searching for news & squads: {game.home_team} vs {game.away_team}...")
            else:
                print(f"🔍 Searching for news & squads: {game.home_team} vs {game.away_team}...")
                
            try:
                search_context = search_client.get_match_context(game.home_team, game.away_team)
                market_context.update(search_context)
                if monitor:
                    monitor.show_success("Real-time data acquired")
                else:
                    print("✅ Real-time data acquired")
            except Exception as e:
                if monitor:
                    monitor.show_error(f"Search failed: {e}")
                else:
                    print(f"❌ Search failed: {e}")

        # Analyze game
        consensus_bet = syndicate.analyze_game(game, market_context)

        if consensus_bet:
            # Save bet for later matching with real results
            if db and simulation_id and hasattr(consensus_bet, 'id'):
                # Bet already saved in place_bet() with outcome="pending"
                pass

            # Add to results (without outcome - to be filled later with real results)
            results.append({
                "game": f"{game.away_team} @ {game.home_team}",
                "bet": consensus_bet.team,
                "stake": consensus_bet.stake,
                "confidence": consensus_bet.confidence,
                "reasoning": getattr(consensus_bet, 'reasoning', 'No reasoning provided')
            })

        bankroll_manager.take_snapshot()
        games_analyzed += 1

        # Stop if bankroll depleted
        if bankroll_manager.current_bankroll <= 0:
            if monitor:
                monitor.show_error("BANKROLL DEPLETED - Simulation ended early")
            else:
                print("\n💀 BANKROLL DEPLETED - Simulation ended early")
            break

    # Final statistics
    if not monitor:
        print("\n" + "=" * 70)
        print("📊 SIMULATION COMPLETE")
        print("=" * 70)

    # Note: No simulated outcomes or stats calculation since we're collecting bets for later real result matching
    agent_stats = syndicate.get_agent_stats()
    
    # Store bets in DB for later matching with real results
    if db and user_id and simulation_id:
        duration = (datetime.utcnow() - start_time).seconds
        SimulationStore.save_simulation(
            db=db,
            user_id=user_id,
            simulation_id=simulation_id,
            num_games=num_games,
            starting_bankroll=starting_bankroll,
            kelly_fraction=settings.KELLY_FRACTION,
            sport=sport,
            use_live_data=use_live_data,
            final_bankroll=None,  # Will be calculated after real results come in
            roi=None,
            win_rate=None,
            total_bets=len(results),
            total_wagered=sum(r.get('stake', 0) for r in results),
            max_drawdown=None,
            duration_seconds=duration,
            agent_stats=agent_stats
        )

    if monitor:
        monitor.show_separator()
        monitor.show_success("ANALYSIS COMPLETE")
        monitor.log_event("INFO", f"Collected {len(results)} agent predictions (outcomes pending)")
    else:
        print("\n" + "=" * 70)
        print("🎰 ANALYSIS COMPLETE")
        print("=" * 70)
        print(f"📊 Predictions Collected: {len(results)} games")
        print(f"💾 Stored in database for real result matching")
        print(f"⏳ Waiting for actual match results (end of day/next day)")

    return {
        "agent_stats": agent_stats,
        "results": results,
        "total_bets": len(results),
        "total_wagered": sum(r.get('stake', 0) for r in results)
    }
