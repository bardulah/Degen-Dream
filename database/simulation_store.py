"""Database integration for simulations."""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from database.schema import (
    Simulation, Bet, AgentSimulationStats, User
)
from monitoring.logger import logger


class SimulationStore:
    """Store simulation results in database."""

    @staticmethod
    def save_simulation(
        db: Session,
        user_id: str,
        simulation_id: str,
        num_games: int,
        starting_bankroll: float,
        kelly_fraction: float,
        sport: str,
        use_live_data: bool,
        final_bankroll: float,
        roi: float,
        win_rate: float,
        total_bets: int,
        total_wagered: float,
        max_drawdown: float,
        duration_seconds: int,
        agent_stats: List[Dict[str, Any]]
    ) -> bool:
        """
        Save simulation results to database.
        
        Args:
            db: Database session
            user_id: User ID
            simulation_id: Simulation ID
            ... (all simulation parameters)
            agent_stats: List of agent stat dictionaries
        
        Returns:
            True if successful
        """
        try:
            # Update simulation record
            simulation = db.query(Simulation).filter(
                Simulation.id == simulation_id
            ).first()
            
            if not simulation:
                logger.error(f"Simulation not found: {simulation_id}")
                return False
            
            # Only update non-None values (results come in later)
            if final_bankroll is not None:
                simulation.final_bankroll = final_bankroll
            if roi is not None:
                simulation.roi = roi
            if win_rate is not None:
                simulation.win_rate = win_rate
            if max_drawdown is not None:
                simulation.max_drawdown = max_drawdown
            
            simulation.total_bets = total_bets
            simulation.total_wagered = total_wagered
            simulation.duration_seconds = duration_seconds
            simulation.status = "pending_results" if roi is None else "completed"
            simulation.updated_at = datetime.utcnow()
            
            # Save agent stats
            for stat in agent_stats:
                agent_stat = AgentSimulationStats(
                    id=str(uuid.uuid4()),
                    simulation_id=simulation_id,
                    agent_name=stat["name"],
                    agent_type=stat["type"],
                    initial_bankroll=stat["initial_bankroll"],
                    final_bankroll=stat["bankroll"],
                    roi=stat["roi"],
                    total_bets=stat["total_bets"],
                    wins=stat["wins"],
                    losses=stat["losses"],
                    win_rate=stat["win_rate"],
                    profit_loss=stat["profit_loss"]
                )
                db.add(agent_stat)
            
            # Update user stats
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Reset daily counter if needed (in production, use scheduled task)
                user.total_simulations += 1
            
            db.commit()
            
            logger.log_simulation_end(user_id, simulation_id, roi, win_rate)
            return True
        
        except Exception as e:
            import traceback
            logger.error(f"Failed to save simulation: {str(e)}", user_id=user_id)
            print(f"ERROR saving simulation: {e}")
            print(traceback.format_exc())
            db.rollback()
            return False

    @staticmethod
    def save_bet(
        db: Session,
        simulation_id: str,
        agent_name: str,
        game_home_team: str,
        game_away_team: str,
        sport: str,
        bet_team: str,
        bet_type: str,
        line: float,
        odds: float,
        stake: float,
        confidence: float,
        reasoning: str
    ) -> Optional[str]:
        """Save individual bet to database. Returns bet ID."""
        try:
            bet_id = str(uuid.uuid4())
            bet = Bet(
                id=bet_id,
                simulation_id=simulation_id,
                agent_name=agent_name,
                game_home_team=game_home_team,
                game_away_team=game_away_team,
                sport=sport,
                bet_team=bet_team,
                bet_type=bet_type,
                line=line,
                odds=odds,
                stake=stake,
                confidence=confidence,
                reasoning=reasoning,
                created_at=datetime.utcnow()
            )
            
            db.add(bet)
            db.commit()
            
            logger.log_bet_placed(simulation_id, agent_name, bet_team, stake, odds)
            return bet_id
        
        except Exception as e:
            logger.error(f"Failed to save bet: {str(e)}")
            db.rollback()
            return None



    @staticmethod
    def get_simulation_bets(
        db: Session,
        simulation_id: str
    ) -> List[Bet]:
        """Get all bets from a simulation."""
        return db.query(Bet).filter(Bet.simulation_id == simulation_id).all()

    @staticmethod
    def get_user_simulations(
        db: Session,
        user_id: str,
        limit: int = 10
    ) -> List[Simulation]:
        """Get user's recent simulations."""
        return db.query(Simulation)\
            .filter(Simulation.user_id == user_id)\
            .order_by(Simulation.created_at.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def mark_simulation_failed(
        db: Session,
        simulation_id: str,
        error_message: str
    ) -> bool:
        """Mark simulation as failed."""
        try:
            simulation = db.query(Simulation).filter(
                Simulation.id == simulation_id
            ).first()
            
            if not simulation:
                return False
            
            simulation.status = "failed"
            simulation.error_message = error_message
            simulation.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.error(f"Simulation failed: {error_message}", 
                        simulation_id=simulation_id)
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark simulation failed: {str(e)}")
            return False
