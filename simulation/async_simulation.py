"""Async/parallel simulation support for faster agent analysis."""

import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sqlalchemy.orm import Session

from agents.base_agent import Game, Bet
from simulation.bankroll import BankrollManager
from monitoring.logger import logger


class AsyncAgentAnalyzer:
    """Manages parallel/concurrent LLM calls for agent analysis."""

    def __init__(self, max_workers: int = 5):
        """Initialize async analyzer.
        
        Args:
            max_workers: Maximum number of concurrent LLM calls
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.analysis_times: Dict[str, float] = {}

    def analyze_game_sync(self, agent: Any, game: Game, context: Dict[str, Any]) -> Optional[Bet]:
        """Synchronous wrapper for agent analysis.
        
        Args:
            agent: Agent instance
            game: Game to analyze
            context: Additional context
            
        Returns:
            Bet object if agent wants to bet, None otherwise
        """
        try:
            start = datetime.utcnow()
            result = agent.analyze_game(game, context)
            elapsed = (datetime.utcnow() - start).total_seconds()
            self.analysis_times[agent.name] = elapsed
            return result
        except Exception as e:
            logger.error(f"Agent {agent.name} analysis failed: {e}")
            return None

    async def analyze_game_async(self, agent: Any, game: Game, context: Dict[str, Any]) -> Optional[Bet]:
        """Async wrapper for agent analysis using thread pool.
        
        Args:
            agent: Agent instance
            game: Game to analyze
            context: Additional context
            
        Returns:
            Bet object if agent wants to bet, None otherwise
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                self.executor,
                self.analyze_game_sync,
                agent,
                game,
                context
            )
        except Exception as e:
            logger.error(f"Async analysis failed for {agent.name}: {e}")
            return None

    async def analyze_all_agents(
        self,
        agents: List[Any],
        game: Game,
        context: Dict[str, Any]
    ) -> List[Optional[Bet]]:
        """Analyze game for all agents in parallel.
        
        Args:
            agents: List of agents to analyze
            game: Game to analyze
            context: Additional context
            
        Returns:
            List of Bet objects (or None) in agent order
        """
        tasks = [
            self.analyze_game_async(agent, game, context)
            for agent in agents
        ]
        
        # Run all analyses concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        return results

    def get_analysis_stats(self) -> Dict[str, float]:
        """Get analysis time statistics per agent.
        
        Returns:
            Dict of agent_name -> average_analysis_time
        """
        return self.analysis_times.copy()

    def reset_stats(self):
        """Reset analysis statistics."""
        self.analysis_times.clear()

    def shutdown(self):
        """Shutdown thread pool executor."""
        self.executor.shutdown(wait=True)


class ParallelDebateManager:
    """Manages parallel processing of agent debates."""

    def __init__(self, max_workers: int = 3):
        """Initialize debate manager.
        
        Args:
            max_workers: Maximum concurrent debate threads
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def generate_debate_statement_async(
        self,
        agent: Any,
        context: Dict[str, Any],
        other_agents: List[Any]
    ) -> Optional[str]:
        """Generate debate statement asynchronously.
        
        Args:
            agent: Agent providing statement
            context: Debate context (game, bets, etc.)
            other_agents: Other agents in debate
            
        Returns:
            Statement string or None
        """
        loop = asyncio.get_event_loop()
        try:
            def sync_debate():
                return agent.debate(context, other_agents)
            
            return await loop.run_in_executor(self.executor, sync_debate)
        except Exception as e:
            logger.error(f"Debate failed for {agent.name}: {e}")
            return None

    async def run_debate_round(
        self,
        agents: List[Any],
        context: Dict[str, Any]
    ) -> Dict[str, Optional[str]]:
        """Run one round of debate with all agents in parallel.
        
        Args:
            agents: List of agents debating
            context: Debate context
            
        Returns:
            Dict of agent_name -> statement
        """
        tasks = {
            agent.name: self.generate_debate_statement_async(agent, context, agents)
            for agent in agents
        }
        
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=False
        )
        
        return {
            name: stmt
            for name, stmt in zip(tasks.keys(), results)
        }

    def shutdown(self):
        """Shutdown executor."""
        self.executor.shutdown(wait=True)


def run_async_simulation(
    agents: List[Any],
    game: Game,
    context: Dict[str, Any],
    max_workers: int = 5
) -> List[Optional[Bet]]:
    """Run agent analysis asynchronously (blocking wrapper).
    
    This function runs the async event loop and returns results
    for use in synchronous code (like the main simulation loop).
    
    Args:
        agents: List of agents
        game: Game to analyze
        context: Debate context
        max_workers: Max concurrent LLM calls
        
    Returns:
        List of agent bets
    """
    analyzer = AsyncAgentAnalyzer(max_workers=max_workers)
    
    try:
        # Create new event loop for this call (safe for thread usage)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            analyzer.analyze_all_agents(agents, game, context)
        )
        
        return results
    finally:
        analyzer.shutdown()
        loop.close()


async def run_async_debate(
    agents: List[Any],
    context: Dict[str, Any],
    max_workers: int = 3
) -> Dict[str, Optional[str]]:
    """Run debate asynchronously.
    
    Args:
        agents: List of agents debating
        context: Debate context
        max_workers: Max concurrent debate threads
        
    Returns:
        Dict of agent_name -> statement
    """
    manager = ParallelDebateManager(max_workers=max_workers)
    
    try:
        return await manager.run_debate_round(agents, context)
    finally:
        manager.shutdown()
