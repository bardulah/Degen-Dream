"""FastAPI service for Bratislava Betting Syndicate."""

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import Optional
import os
import stripe
from pathlib import Path

from database.schema import init_db, get_db, User, UserTier, Simulation, Bet, CustomAgent
from database.auth import auth_manager, RateLimiter
from monitoring.logger import logger
from .routes import auth, simulations, agents, subscriptions

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Bratislava Betting Syndicate API",
    description="Multi-agent AI betting simulation API",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8501").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_")

# Include routers (API routes have priority)
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(simulations.router, prefix="/api/simulations", tags=["simulations"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])

# Mount static files (serve dashboard)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected"
    }


@app.get("/api/user/profile")
async def get_user_profile(
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get current user's profile."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "tier": user.tier.value,
        "created_at": user.created_at.isoformat(),
        "simulations_run_today": user.simulations_run_today,
        "total_simulations": user.total_simulations,
        "custom_agents_created": user.custom_agents_created,
        "api_key": user.api_key if user.api_key else "Not generated"
    }


@app.post("/api/user/generate-api-key")
async def generate_api_key(
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Generate a new API key for the user."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check tier
    tier = auth_manager.get_user_tier(db, user_id)
    if tier not in [UserTier.PRO, UserTier.ENTERPRISE]:
        raise HTTPException(
            status_code=403,
            detail="API key generation only available in Pro+ tiers"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.api_key = auth_manager.generate_api_key()
    db.commit()
    
    logger.info(f"API key generated for user {user_id}")
    
    return {"api_key": user.api_key}


@app.get("/api/stats/overview")
async def get_user_stats(
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get user's overall statistics."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    simulations = db.query(Simulation).filter(Simulation.user_id == user_id).all()
    
    total_roi = 0
    total_bets = 0
    wins = 0
    
    for sim in simulations:
        total_roi += sim.roi
        total_bets += sim.total_bets
        wins += int(sim.total_bets * sim.win_rate / 100)
    
    avg_roi = total_roi / len(simulations) if simulations else 0
    avg_win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    
    return {
        "total_simulations": user.total_simulations,
        "total_bets_placed": total_bets,
        "total_wins": wins,
        "average_roi": round(avg_roi, 2),
        "average_win_rate": round(avg_win_rate, 1),
        "custom_agents_created": user.custom_agents_created,
        "account_tier": user.tier.value
    }


@app.get("/api/dashboard")
async def get_dashboard(
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get dashboard data with recent simulations."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get recent simulations
    simulations = db.query(Simulation)\
        .filter(Simulation.user_id == user_id)\
        .order_by(Simulation.created_at.desc())\
        .limit(10)\
        .all()
    
    sim_data = []
    for sim in simulations:
        sim_data.append({
            "id": sim.id,
            "sport": sim.sport,
            "status": sim.status,
            "num_games": sim.num_games,
            "roi": round(sim.roi, 2) if sim.roi else 0,
            "win_rate": round(sim.win_rate, 1) if sim.win_rate else 0,
            "total_bets": sim.total_bets or 0,
            "profit": round((sim.final_bankroll or 0) - sim.starting_bankroll, 2) if sim.final_bankroll else 0,
            "created_at": sim.created_at.isoformat(),
            "duration_seconds": sim.duration_seconds or 0
        })
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "tier": user.tier.value
        },
        "simulations": sim_data,
        "stats": {
            "total_simulations": user.total_simulations,
            "custom_agents": user.custom_agents_created,
            "simulations_today": user.simulations_run_today
        }
    }


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Bratislava Betting Syndicate API starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Bratislava Betting Syndicate API shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        workers=int(os.getenv("API_WORKERS", 4))
    )
