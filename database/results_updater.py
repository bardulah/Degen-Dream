"""Update bet results in database after matches are settled."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database.schema import Base, Bet, Simulation, BetOutcome
from data.results_matcher import ResultsMatcher
from agents.base_agent import Game
import os


class ResultsUpdater:
    """Updates bet results in database after matches are settled."""
    
    def __init__(self, database_url: str):
        """Initialize results updater.
        
        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.matcher = ResultsMatcher()
    
    def update_pending_bets(self, game_results: List[Game]) -> Dict[str, Any]:
        """Update all PENDING bets with real results.
        
        Args:
            game_results: List of Game objects with scores
        
        Returns:
            Dictionary with update statistics
        """
        session = self.SessionLocal()
        
        try:
            # Fetch all pending bets
            pending_bets = session.query(Bet).filter(
                Bet.outcome == BetOutcome.PENDING
            ).all()
            
            if not pending_bets:
                print("✅ No pending bets to update")
                return {"updated": 0, "matched": 0, "unmatched": 0}
            
            print(f"📊 Updating {len(pending_bets)} pending bets...")
            
            stats = {
                "updated": 0,
                "matched": 0,
                "unmatched": 0,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            }
            
            # Match results
            results = self.matcher.match_results(pending_bets, game_results)
            
            for bet, outcome, profit_loss in results:
                try:
                    # Update bet record
                    bet.outcome = outcome
                    bet.profit_loss = profit_loss
                    
                    # Track statistics
                    stats["updated"] += 1
                    if outcome == BetOutcome.WON:
                        stats["wins"] += 1
                        stats["total_profit"] += profit_loss
                    elif outcome == BetOutcome.LOST:
                        stats["losses"] += 1
                        stats["total_loss"] += abs(profit_loss)
                    elif outcome == BetOutcome.PUSH:
                        stats["pushes"] += 1
                    
                    session.commit()
                    
                    # Print update
                    outcome_emoji = "✅" if outcome == BetOutcome.WON else "❌" if outcome == BetOutcome.LOST else "➖"
                    print(f"{outcome_emoji} {bet.agent_name}: {bet.bet_team} {bet.bet_type} "
                          f"→ {outcome.value} (€{profit_loss:+.2f})")
                    
                except Exception as e:
                    print(f"❌ Error updating bet {bet.id}: {e}")
                    session.rollback()
                    continue
            
            stats["matched"] = stats["updated"]
            stats["unmatched"] = len(pending_bets) - stats["updated"]
            
            return stats
            
        finally:
            session.close()
    
    def update_simulation_metrics(self, simulation_id: str) -> bool:
        """Update simulation metrics after bets are settled.
        
        Args:
            simulation_id: Simulation ID to update
        
        Returns:
            True if successful
        """
        session = self.SessionLocal()
        
        try:
            # Get simulation and its bets
            simulation = session.query(Simulation).filter(
                Simulation.id == simulation_id
            ).first()
            
            if not simulation:
                print(f"❌ Simulation not found: {simulation_id}")
                return False
            
            # Get all settled bets for this simulation
            bets = session.query(Bet).filter(
                Bet.simulation_id == simulation_id,
                Bet.outcome != BetOutcome.PENDING
            ).all()
            
            if not bets:
                print(f"⚠️  No settled bets for simulation {simulation_id}")
                return False
            
            # Calculate metrics
            wins = sum(1 for b in bets if b.outcome == BetOutcome.WON)
            losses = sum(1 for b in bets if b.outcome == BetOutcome.LOST)
            total_profit = sum(b.profit_loss for b in bets if b.profit_loss and b.outcome == BetOutcome.WON)
            total_loss = sum(abs(b.profit_loss) for b in bets if b.profit_loss and b.outcome == BetOutcome.LOST)
            
            # Update simulation record
            simulation.total_bets = len(bets)
            simulation.win_rate = (wins / len(bets) * 100) if bets else 0.0
            simulation.final_bankroll = simulation.starting_bankroll + total_profit - total_loss
            simulation.roi = ((simulation.final_bankroll - simulation.starting_bankroll) / 
                            simulation.starting_bankroll * 100) if simulation.starting_bankroll else 0.0
            simulation.total_wagered = sum(b.stake for b in bets)
            
            session.commit()
            
            print(f"✅ Updated simulation {simulation_id}: "
                  f"{wins}W-{losses}L, ROI: {simulation.roi:.2f}%")
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating simulation metrics: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_agent_accuracy(self, agent_name: str, days: int = 7) -> Dict[str, Any]:
        """Calculate agent accuracy over recent period.
        
        Args:
            agent_name: Name of agent
            days: Number of days to look back
        
        Returns:
            Dictionary with accuracy metrics
        """
        session = self.SessionLocal()
        
        try:
            # Get all settled bets for agent
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            bets = session.query(Bet).filter(
                Bet.agent_name == agent_name,
                Bet.created_at >= cutoff_date,
                Bet.outcome != BetOutcome.PENDING
            ).all()
            
            if not bets:
                return {
                    "agent": agent_name,
                    "bets": 0,
                    "win_rate": 0.0,
                    "confidence_calibration": 0.0,
                    "roi": 0.0,
                    "avg_confidence": 0.0,
                }
            
            # Calculate metrics
            wins = sum(1 for b in bets if b.outcome == BetOutcome.WON)
            win_rate = wins / len(bets) * 100 if bets else 0.0
            
            avg_confidence = sum(b.confidence for b in bets) / len(bets) if bets else 0.0
            confidence_calibration = abs(win_rate / 100 - avg_confidence) if avg_confidence else 0.0
            
            total_profit = sum(b.profit_loss for b in bets if b.profit_loss)
            total_wagered = sum(b.stake for b in bets)
            roi = (total_profit / total_wagered * 100) if total_wagered else 0.0
            
            return {
                "agent": agent_name,
                "bets": len(bets),
                "wins": wins,
                "losses": len(bets) - wins,
                "win_rate": win_rate,
                "confidence_calibration": confidence_calibration,
                "roi": roi,
                "avg_confidence": avg_confidence,
                "total_profit": total_profit,
                "total_wagered": total_wagered,
            }
            
        finally:
            session.close()
    
    def get_leaderboard(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Get agent leaderboard.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of agents to return
        
        Returns:
            List of agent accuracy dictionaries, sorted by ROI
        """
        session = self.SessionLocal()
        
        try:
            # Get all unique agents with settled bets
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            agents = session.query(Bet.agent_name).filter(
                Bet.created_at >= cutoff_date,
                Bet.outcome != BetOutcome.PENDING
            ).distinct().all()
            
            if not agents:
                return []
            
            leaderboard = []
            for (agent_name,) in agents:
                stats = self.get_agent_accuracy(agent_name, days)
                if stats["bets"] > 0:  # Only include agents with bets
                    leaderboard.append(stats)
            
            # Sort by ROI descending
            leaderboard.sort(key=lambda x: x["roi"], reverse=True)
            
            return leaderboard[:limit]
            
        finally:
            session.close()
    
    def print_leaderboard(self, days: int = 7):
        """Print formatted leaderboard.
        
        Args:
            days: Number of days to look back
        """
        leaderboard = self.get_leaderboard(days)
        
        if not leaderboard:
            print(f"No data for leaderboard (last {days} days)")
            return
        
        print("\n" + "=" * 80)
        print(f"🏆 AGENT LEADERBOARD (Last {days} Days)")
        print("=" * 80)
        
        for i, agent in enumerate(leaderboard, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            print(f"\n{emoji} {agent['agent']}")
            print(f"   💰 ROI: {agent['roi']:+.2f}% | "
                  f"Win Rate: {agent['win_rate']:.1f}% | "
                  f"Confidence: {agent['avg_confidence']:.0%}")
            print(f"   📊 {agent['wins']}W-{agent['losses']}L | "
                  f"Profit: €{agent['total_profit']:+.2f}")
            print(f"   📈 Calibration Error: {agent['confidence_calibration']:.2f}")
        
        print("\n" + "=" * 80)
    
    async def post_leaderboard_to_discord(self, days: int = 7) -> bool:
        """Post agent leaderboard to Discord.
        
        Args:
            days: Number of days to look back
        
        Returns:
            True if posted successfully
        """
        # Check if Discord is configured
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            print("⚠️  Discord webhook not configured - skipping leaderboard post")
            return False
        
        # Import here to avoid circular imports
        from notification.discord_notifier import DiscordNotifier
        
        # Get leaderboard data
        leaderboard = self.get_leaderboard(days)
        if not leaderboard:
            print(f"⚠️  No leaderboard data for last {days} days")
            return False
        
        # Format for Discord
        leaderboard_data = []
        for i, agent in enumerate(leaderboard, 1):
            rank = i
            agent_name = agent["agent"]
            roi = agent["roi"]
            win_rate = agent["win_rate"]
            record = f"{agent['wins']}W-{agent['losses']}L"
            stats = agent
            
            leaderboard_data.append((rank, agent_name, roi, win_rate, record, stats))
        
        # Send to Discord
        notifier = DiscordNotifier(webhook_url)
        success = await notifier.send_leaderboard_embed(leaderboard_data)
        
        if success:
            print("✅ Leaderboard posted to Discord")
        else:
            print("⚠️  Failed to post leaderboard to Discord")
        
        return success
