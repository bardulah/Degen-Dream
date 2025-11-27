"""LangGraph orchestration for multi-agent betting syndicate."""

import uuid
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
import random
from datetime import datetime
from sqlalchemy.orm import Session
import asyncio

from agents.base_agent import Game, Bet
from agents.sharp_agent import SharpAgent
from agents.insider_agent import InsiderAgent
from agents.degen_agent import DegenAgent
from agents.bookie_agent import BookieAgent
from agents.oracle_agent import OracleAgent
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
    agent_votes: Dict[str, int]  # Track votes: team -> count


class SyndicateGraph:
    """LangGraph-based multi-agent betting syndicate."""

    def __init__(
        self,
        agents: Optional[List] = None,
        bankroll_manager: Optional[BankrollManager] = None,
        db: Optional[Session] = None,
        simulation_id: Optional[str] = None,
        notifier: Optional[Any] = None
    ):
        """Initialize syndicate graph.

        Args:
            agents: List of agents (if None, creates default 10)
            bankroll_manager: Bankroll manager instance
            db: Database session (optional)
            simulation_id: Simulation ID (optional)
            notifier: Discord notifier (optional)
        """
        self.agents = agents or self._create_default_agents()
        self.oracle = OracleAgent()  # The Oracle analyzes all picks
        self.bankroll_manager = bankroll_manager or BankrollManager(
            settings.STARTING_BANKROLL
        )
        self.kelly_calculator = KellyCalculator(fraction=settings.KELLY_FRACTION)
        self.db = db
        self.simulation_id = simulation_id
        self.notifier = notifier

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
                
                # Send to Discord if enabled
                if hasattr(self, 'notifier') and self.notifier and self.notifier.enabled:
                    try:
                        asyncio.run(self.notifier.on_agent_analyzed(
                            agent_name=agent.name,
                            agent_type=agent.agent_type.value,
                            bet=bet
                        ))
                        asyncio.run(self.notifier.send_separator())
                    except Exception as e:
                        print(f"Discord notification failed: {e}")
            else:
                if not (hasattr(self, 'monitor') and self.monitor):
                    print(f"❌ {agent.name} ({agent.agent_type.value}): Pass\n")
                
                # Send to Discord if enabled
                if hasattr(self, 'notifier') and self.notifier and self.notifier.enabled:
                    try:
                        asyncio.run(self.notifier.on_agent_analyzed(
                            agent_name=agent.name,
                            agent_type=agent.agent_type.value,
                            bet=None
                        ))
                        asyncio.run(self.notifier.send_separator())
                    except Exception as e:
                        print(f"Discord notification failed: {e}")

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
            
            # Send to Discord if enabled
            if hasattr(self, 'notifier') and self.notifier and self.notifier.enabled:
                try:
                    asyncio.run(self.notifier.on_debate_message(
                        agent_name=agent.name,
                        message=response
                    ))
                except Exception as e:
                    print(f"Discord notification failed: {e}")

        state["debate_history"] = debate_history
        return state

    def _vote(self, state: SyndicateState) -> SyndicateState:
        """Vote on which bet to place (Oracle decides, votes for comparison).
        
        The Oracle analyzes all agent picks, their reasoning, and conviction levels,
        then makes an informed decision on which bet to place. Democratic vote is
        kept for comparison.

        Args:
            state: Current state

        Returns:
            Updated state with consensus bet
        """
        agent_bets = state["agent_bets"]
        game = state["game"]
        market_context = state.get("market_context", {})

        if not agent_bets:
            state["consensus_bet"] = None
            state["agent_votes"] = {}
            return state

        if not (hasattr(self, 'monitor') and self.monitor):
            print("\n🗳️  VOTING vs 🔮 ORACLE ANALYSIS")
            print("=" * 60)

        # Democratic vote count
        team_votes = {}
        team_bets = {}
        for bet in agent_bets:
            team = bet.team
            if team not in team_votes:
                team_votes[team] = 0
                team_bets[team] = []
            team_votes[team] += 1
            team_bets[team].append(bet)

        # Get democratic winner
        vote_winner = max(team_votes, key=team_votes.get)
        vote_winner_bets = team_bets[vote_winner]
        vote_winner_bet = max(vote_winner_bets, key=lambda b: b.stake + b.confidence)

        # Get Oracle's decision
        oracle_bet = self.oracle.analyze_picks(game, agent_bets, market_context)

        if not (hasattr(self, 'monitor') and self.monitor):
            votes_str = ", ".join([f"{t}: {v} vote{'s' if v > 1 else ''}" for t, v in team_votes.items()])
            print(f"📊 DEMOCRATIC VOTE: {vote_winner} ({votes_str})")
            print(f"   Pick: {vote_winner_bet.team} by {vote_winner_bet.agent_name}")
            print(f"   Conviction: {vote_winner_bet.confidence:.0%}\n")

            if oracle_bet:
                match_symbol = "✅" if oracle_bet.team == vote_winner else "⚠️ "
                print(f"{match_symbol} ORACLE DECISION: Bet on {oracle_bet.team}")
                print(f"   Reasoning: {oracle_bet.reasoning}")
                print(f"   Conviction: {oracle_bet.confidence:.0%}")
                if oracle_bet.team != vote_winner:
                    print(f"   (Differs from vote winner: {vote_winner})\n")
                else:
                    print(f"   (Agrees with democratic consensus)\n")

        state["consensus_bet"] = oracle_bet or vote_winner_bet  # Oracle if available, else vote winner
        state["agent_votes"] = team_votes  # Store vote breakdown
        return state

    def _oracle_decides(self, agent_bets: List[Bet]) -> tuple:
        """Oracle picks the winning bet from all agent votes.
        
        Algorithm:
        1. Count votes for each team/outcome
        2. The team with most votes wins (democratic)
        3. Among bets on that team, pick the one with highest combined score
           (stake + confidence)
        
        Args:
            agent_bets: All bets proposed by agents
            
        Returns:
            Tuple of (oracle's chosen bet, vote breakdown dict)
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
        
        return best_bet, team_votes

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
                    reasoning=consensus_bet.reasoning
                )
                if bet_id:
                    consensus_bet.id = bet_id  # Monkey-patch ID onto bet object
        else:
            print(f"❌ INSUFFICIENT FUNDS to place bet\n")

        return state

    def analyze_game(self, game: Game, market_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the full multi-agent workflow on a game.

        Args:
            game: Game to analyze
            market_context: Additional market data

        Returns:
            Dict containing consensus bet, agent votes, and full state
        """
        initial_state: SyndicateState = {
            "game": game,
            "agent_bets": [],
            "debate_history": [],
            "consensus_bet": None,
            "market_context": market_context or {},
            "agent_votes": {}
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        return final_state

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
    use_live_data: bool = False,
    notifier: Optional[Any] = None
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
        notifier: Optional Discord notifier

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
        simulation_id=simulation_id,
        notifier=notifier  # Pass Discord notifier
    )
    # Override bankroll if needed (constructor creates one with default starting bankroll from settings, 
    # but we want to use the passed starting_bankroll)
    syndicate.bankroll_manager = BankrollManager(starting_bankroll)
    
    syndicate.monitor = monitor  # Pass monitor to syndicate
    bankroll_manager = syndicate.bankroll_manager
    
    # Initialize Search Client (Real-time context for agents)
    search_enabled = False
    search_client = None
    try:
        from data.gemini_search import GeminiSearchClient
        search_client = GeminiSearchClient()
        search_enabled = True
        if monitor:
            monitor.log_event("INFO", "✅ Gemini Search Grounding enabled")
        else:
            print("🔍 Gemini Search Grounding enabled (real-time injury/news data)")
    except Exception as e:
        search_enabled = False
        if monitor:
            monitor.show_warning(f"Gemini Search disabled: {e}")
        else:
            print(f"⚠️  Gemini Search disabled: {e}")

    results = []
    games_analyzed = 0
    
    # Track all bets by agent for parlay generation
    agent_all_bets = {}  # agent_name -> list of bets

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
                
                # Standardize context keys for agent consumption
                if search_context:
                    # Flatten search context into format agents expect
                    real_time_info = []
                    if search_context.get("news"):
                        real_time_info.append(f"📰 TEAM NEWS & INJURIES:\n{search_context['news']}")
                    if search_context.get("form"):
                        real_time_info.append(f"📊 RECENT FORM:\n{search_context['form']}")
                    if search_context.get("sentiment"):
                        real_time_info.append(f"🎯 EXPERT PREDICTIONS:\n{search_context['sentiment']}")
                    
                    market_context["real_time_data"] = "\n\n".join(real_time_info) if real_time_info else ""
                    market_context["injury_news"] = search_context.get("news", "")
                    market_context["news_context"] = search_context.get("news", "")
                
                if monitor:
                    monitor.show_success("Real-time data acquired")
                else:
                    print("✅ Real-time data acquired")
            except Exception as e:
                if monitor:
                    monitor.show_error(f"Search failed: {e}")
                else:
                    print(f"❌ Search failed: {e}")
                market_context["real_time_data"] = ""

        # Analyze game
        state = syndicate.analyze_game(game, market_context)
        consensus_bet = state.get("consensus_bet")
        agent_bets = state.get("agent_bets", [])
        agent_votes = state.get("agent_votes", {})
        
        # Track all bets by agent for parlay generation
        for bet in agent_bets:
            if bet.agent_name not in agent_all_bets:
                agent_all_bets[bet.agent_name] = []
            agent_all_bets[bet.agent_name].append(bet)
        
        # Notify Discord of oracle decision
        if consensus_bet and notifier and notifier.enabled:
            try:
                # Add matchup info to consensus bet for Discord message
                if not hasattr(consensus_bet, 'matchup'):
                    consensus_bet.matchup = f"{game.away_team} @ {game.home_team}"
                asyncio.run(notifier.on_oracle_decision(consensus_bet, agent_votes))
            except Exception as e:
                print(f"Discord notification failed: {e}")

        if consensus_bet:
            # Save bet for later matching with real results
            if db and simulation_id and hasattr(consensus_bet, 'id'):
                # Bet already saved in place_bet() with outcome="pending"
                pass

            # Build voting summary (for comparison)
            voting_summary = "Vote breakdown: "
            if agent_votes:
                voting_summary += ", ".join([f"{team}: {votes} vote{'s' if votes > 1 else ''}" for team, votes in agent_votes.items()])
            
            # Build oracle decision summary
            oracle_summary = f"Oracle: {consensus_bet.agent_name}'s bet on {consensus_bet.team}"
            oracle_summary += f" | Conviction: {consensus_bet.confidence:.0%}"

            # Get all agent bets for full context
            all_reasoning = "\n\n".join([
                f"• {bet.agent_name}: {bet.team} ({bet.bet_type}) @ {bet.odds:.2f} - {bet.reasoning}"
                for bet in agent_bets
            ])

            # Add to results (without outcome - to be filled later with real results)
            results.append({
                "game": f"{game.away_team} @ {game.home_team}",
                "home_team": game.home_team,
                "away_team": game.away_team,
                "home_odds": game.home_odds,
                "away_odds": game.away_odds,
                "draw_odds": getattr(game, 'draw_odds', None),
                "bet": consensus_bet.team,
                "bet_type": consensus_bet.bet_type,
                "odds": consensus_bet.odds,
                "stake": consensus_bet.stake,
                "confidence": consensus_bet.confidence,
                "oracle_decision": oracle_summary,
                "voting_summary": voting_summary,
                "agent_votes": agent_votes,
                "consensus_agent": consensus_bet.agent_name,
                "consensus_bet": consensus_bet,  # Store full bet object for parlay generation
                "reasoning": getattr(consensus_bet, 'reasoning', 'No reasoning provided'),
                "all_agent_analysis": all_reasoning
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

    # Generate parlays for each agent
    parlays = []
    if agent_all_bets:
        # Get agents from syndicate
        agents = syndicate.agents
        agent_name_to_obj = {agent.name: agent for agent in agents}
        
        for agent_name, bets in agent_all_bets.items():
            if agent_name in agent_name_to_obj:
                agent = agent_name_to_obj[agent_name]
                parlay = agent.create_parlay(bets, min_legs=2, max_legs=5)
                if parlay:
                    parlays.append(parlay)
                    
                    # Send to Discord
                    if notifier and notifier.enabled:
                        try:
                            parlay_message = (
                                f"🎯 {parlay['agent_name']} ({parlay['agent_type'].upper()}) PARLAY\n"
                                f"   {parlay['legs']} legs × {parlay['odds']:.2f} = {parlay['odds']:.2f}x\n"
                                f"   💰 €{parlay['stake']:.2f} | 🔥 {parlay['confidence']:.0%}\n"
                                f"   └─ {parlay['reasoning']}"
                            )
                            asyncio.run(notifier.send_message(parlay_message))
                        except Exception as e:
                            print(f"Discord parlay notification failed: {e}")
        
        # Oracle parlay from consensus bets
        oracle_consensus_bets = [r['consensus_bet'] if 'consensus_bet' in r else None for r in results]
        oracle_consensus_bets = [b for b in oracle_consensus_bets if b]
        
        if oracle_consensus_bets and len(oracle_consensus_bets) >= 2:
            # Sort by confidence descending and take top bets
            top_bets = sorted(oracle_consensus_bets, key=lambda b: b.confidence, reverse=True)[:5]
            
            parlay_odds = 1.0
            for bet in top_bets:
                parlay_odds *= bet.odds
            
            avg_confidence = sum(b.confidence for b in top_bets) / len(top_bets)
            oracle_stake = bankroll_manager.initial_bankroll * 0.05  # 5% for Oracle parlay
            
            oracle_parlay = {
                "agent_name": "🔮 Oracle",
                "agent_type": "oracle",
                "legs": len(top_bets),
                "bets": top_bets,
                "odds": parlay_odds,
                "stake": oracle_stake,
                "confidence": avg_confidence,
                "reasoning": ", ".join([f"{b.team} ({b.odds:.2f})" for b in top_bets])
            }
            parlays.append(oracle_parlay)
            
            if notifier and notifier.enabled:
                try:
                    oracle_message = (
                        f"🎯 🔮 Oracle PARLAY\n"
                        f"   {oracle_parlay['legs']} legs × {oracle_parlay['odds']:.2f} = {oracle_parlay['odds']:.2f}x\n"
                        f"   💰 €{oracle_parlay['stake']:.2f} | 🔥 {oracle_parlay['confidence']:.0%}\n"
                        f"   └─ {oracle_parlay['reasoning']}"
                    )
                    asyncio.run(notifier.send_message(oracle_message))
                except Exception as e:
                    print(f"Discord Oracle parlay notification failed: {e}")
    
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
        "parlays": parlays,
        "total_bets": len(results),
        "total_wagered": sum(r.get('stake', 0) for r in results),
        "parlay_count": len(parlays),
        "parlay_total_odds": sum(p.get('odds', 1.0) for p in parlays)
    }
