"""Simulation API routes."""

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

from database.schema import get_db, User, Simulation, Bet, AgentSimulationStats
from database.auth import auth_manager, RateLimiter
from monitoring.logger import logger
from export.pdf_generator import PDFGenerator

router = APIRouter()


class SimulationRequest(BaseModel):
    """Start a new simulation."""
    num_games: int = 100
    starting_bankroll: float = 10000
    kelly_fraction: float = 0.25
    sport: str = "soccer_epl"
    use_live_data: bool = False


class SimulationResponse(BaseModel):
    """Simulation response."""
    id: str
    status: str
    num_games: int
    starting_bankroll: float
    created_at: str


class SimulationResult(BaseModel):
    """Simulation result."""
    id: str
    num_games: int
    starting_bankroll: float
    final_bankroll: float
    roi: float
    win_rate: float
    total_bets: int
    total_wagered: float
    max_drawdown: float
    duration_seconds: int
    created_at: str


class AgentStats(BaseModel):
    """Agent performance stats."""
    agent_name: str
    agent_type: str
    roi: float
    win_rate: float
    total_bets: int
    wins: int
    losses: int
    profit_loss: float


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(
    request: SimulationRequest,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Start a new simulation."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check rate limits
    auth_mgr = auth_manager
    rate_limiter = RateLimiter(db, auth_mgr)
    can_run, message = rate_limiter.can_run_simulation(user_id)
    
    if not can_run:
        logger.warning(f"Simulation blocked - rate limit exceeded", user_id=user_id, reason=message)
        raise HTTPException(status_code=429, detail=message)
    
    # Record simulation attempt
    rate_limiter.record_simulation(user_id)
    
    # Create simulation record
    sim_id = str(uuid.uuid4())
    simulation = Simulation(
        id=sim_id,
        user_id=user_id,
        num_games=request.num_games,
        starting_bankroll=request.starting_bankroll,
        kelly_fraction=request.kelly_fraction,
        sport=request.sport,
        use_live_data=request.use_live_data,
        status="in_progress",
        created_at=datetime.utcnow()
    )
    
    db.add(simulation)
    db.commit()
    
    logger.log_simulation_start(user_id, sim_id, request.num_games, request.sport)
    
    return SimulationResponse(
        id=sim_id,
        status="in_progress",
        num_games=request.num_games,
        starting_bankroll=request.starting_bankroll,
        created_at=simulation.created_at.isoformat()
    )


@router.get("/history", response_model=List[SimulationResult])
async def get_simulation_history(
    user_id: str = Header(None),
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get user's simulation history."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    simulations = db.query(Simulation)\
        .filter(Simulation.user_id == user_id)\
        .order_by(Simulation.created_at.desc())\
        .limit(limit)\
        .all()
    
    results = []
    for sim in simulations:
        results.append(SimulationResult(
            id=sim.id,
            num_games=sim.num_games,
            starting_bankroll=sim.starting_bankroll,
            final_bankroll=sim.final_bankroll or 0,
            roi=sim.roi or 0,
            win_rate=sim.win_rate or 0,
            total_bets=sim.total_bets or 0,
            total_wagered=sim.total_wagered or 0,
            max_drawdown=sim.max_drawdown or 0,
            duration_seconds=sim.duration_seconds or 0,
            created_at=sim.created_at.isoformat()
        ))
    
    return results


@router.get("/{simulation_id}", response_model=SimulationResult)
async def get_simulation(
    simulation_id: str,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get a specific simulation result."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    simulation = db.query(Simulation)\
        .filter(Simulation.id == simulation_id, Simulation.user_id == user_id)\
        .first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return SimulationResult(
        id=simulation.id,
        num_games=simulation.num_games,
        starting_bankroll=simulation.starting_bankroll,
        final_bankroll=simulation.final_bankroll or 0,
        roi=simulation.roi or 0,
        win_rate=simulation.win_rate or 0,
        total_bets=simulation.total_bets or 0,
        total_wagered=simulation.total_wagered or 0,
        max_drawdown=simulation.max_drawdown or 0,
        duration_seconds=simulation.duration_seconds or 0,
        created_at=simulation.created_at.isoformat()
    )


@router.get("/{simulation_id}/agent-stats", response_model=List[AgentStats])
async def get_agent_stats(
    simulation_id: str,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get agent statistics for a simulation."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify simulation belongs to user
    simulation = db.query(Simulation)\
        .filter(Simulation.id == simulation_id, Simulation.user_id == user_id)\
        .first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Get agent stats
    stats = db.query(AgentSimulationStats)\
        .filter(AgentSimulationStats.simulation_id == simulation_id)\
        .all()
    
    results = []
    for stat in stats:
        results.append(AgentStats(
            agent_name=stat.agent_name,
            agent_type=stat.agent_type,
            roi=stat.roi,
            win_rate=stat.win_rate,
            total_bets=stat.total_bets,
            wins=stat.wins,
            losses=stat.losses,
            profit_loss=stat.profit_loss
        ))
    
    return results


@router.get("/{simulation_id}/export-pdf")
async def export_simulation_pdf(
    simulation_id: str,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Export simulation as PDF report."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check tier
    auth_mgr = auth_manager
    rate_limiter = RateLimiter(db, auth_mgr)
    can_export, message = rate_limiter.can_export_pdf(user_id)
    
    if not can_export:
        logger.warning(f"PDF export blocked - {message}", user_id=user_id)
        raise HTTPException(status_code=403, detail=message)
    
    # Get simulation
    simulation = db.query(Simulation)\
        .filter(Simulation.id == simulation_id, Simulation.user_id == user_id)\
        .first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Get agent stats
    agent_stats = db.query(AgentSimulationStats)\
        .filter(AgentSimulationStats.simulation_id == simulation_id)\
        .all()
    
    # Get user email
    user = db.query(User).filter(User.id == user_id).first()
    
    # Generate PDF
    try:
        pdf_gen = PDFGenerator()
        results = {
            "stats": {
                "starting_bankroll": simulation.starting_bankroll,
                "current_bankroll": simulation.final_bankroll,
                "roi": simulation.roi,
                "win_rate": simulation.win_rate,
                "total_bets": simulation.total_bets,
                "total_wagered": simulation.total_wagered,
                "max_drawdown": simulation.max_drawdown,
                "duration_seconds": simulation.duration_seconds
            }
        }
        
        agent_stats_list = [
            {
                "name": stat.agent_name,
                "type": stat.agent_type,
                "roi": stat.roi,
                "win_rate": stat.win_rate,
                "total_bets": stat.total_bets,
                "profit_loss": stat.profit_loss
            }
            for stat in agent_stats
        ]
        
        pdf_path = pdf_gen.generate_report(
            simulation_id,
            user.email,
            results,
            agent_stats_list
        )
        
        logger.info(f"PDF exported: {simulation_id}", user_id=user_id)
        
        return FileResponse(
            path=pdf_path,
            filename=f"simulation_{simulation_id}.pdf",
            media_type="application/pdf"
        )
    
    except Exception as e:
        logger.error(f"PDF export failed: {str(e)}", user_id=user_id)
        raise HTTPException(status_code=500, detail="PDF generation failed")


@router.delete("/{simulation_id}")
async def delete_simulation(
    simulation_id: str,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete a simulation (only own simulations)."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    simulation = db.query(Simulation)\
        .filter(Simulation.id == simulation_id, Simulation.user_id == user_id)\
        .first()
    
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Delete associated bets and stats
    db.query(Bet).filter(Bet.simulation_id == simulation_id).delete()
    db.query(AgentSimulationStats).filter(AgentSimulationStats.simulation_id == simulation_id).delete()
    
    # Delete simulation
    db.delete(simulation)
    db.commit()
    
    logger.info(f"Simulation deleted: {simulation_id}", user_id=user_id)
    
    return {"message": "Simulation deleted"}
