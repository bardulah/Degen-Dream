"""Custom agent management routes."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import uuid
from datetime import datetime

from database.schema import get_db, User, CustomAgent
from database.auth import auth_manager, RateLimiter
from monitoring.logger import logger

router = APIRouter()


class CreateAgentRequest(BaseModel):
    """Create a custom agent."""
    name: str
    agent_type: str  # sharp, insider, degen, bookie
    personality_prompt: str
    strategy_description: str


class CustomAgentResponse(BaseModel):
    """Custom agent response."""
    id: str
    name: str
    agent_type: str
    version: int
    created_at: str
    roi: float
    total_bets: int
    win_rate: float


class AgentListResponse(BaseModel):
    """List of agents."""
    default_agents: List[dict]
    custom_agents: List[CustomAgentResponse]


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """List default and custom agents."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Default agents
    default_agents = [
        {"name": "Viktor", "type": "sharp", "description": "Expected value or bust"},
        {"name": "Elena", "type": "sharp", "description": "Pinnacle closing line value only"},
        {"name": "Boris", "type": "sharp", "description": "Market inefficiencies arbitrage"},
        {"name": "Nikolai", "type": "insider", "description": "I know a guy at Niké..."},
        {"name": "Petra", "type": "insider", "description": "The fix is in, trust me"},
        {"name": "Jozef", "type": "degen", "description": "YOLO parlay time!"},
        {"name": "Marian", "type": "degen", "description": "My horoscope says OVER"},
        {"name": "Lucia", "type": "degen", "description": "Always bet on red... I mean home teams"},
        {"name": "Tomáš", "type": "bookie", "description": "Time to shade this line..."},
        {"name": "Katarína", "type": "bookie", "description": "Let's trap the squares"}
    ]
    
    # Custom agents
    custom_agents_db = db.query(CustomAgent)\
        .filter(CustomAgent.user_id == user_id, CustomAgent.is_active == True)\
        .all()
    
    custom_agents = [
        CustomAgentResponse(
            id=agent.id,
            name=agent.name,
            agent_type=agent.agent_type,
            version=agent.version,
            created_at=agent.created_at.isoformat(),
            roi=agent.roi,
            total_bets=agent.total_bets,
            win_rate=(agent.wins / agent.total_bets * 100) if agent.total_bets > 0 else 0
        )
        for agent in custom_agents_db
    ]
    
    return AgentListResponse(
        default_agents=default_agents,
        custom_agents=custom_agents
    )


@router.post("/custom", response_model=CustomAgentResponse)
async def create_custom_agent(
    request: CreateAgentRequest,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Create a custom agent."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check tier
    auth_mgr = auth_manager
    rate_limiter = RateLimiter(db, auth_mgr)
    can_create, message = rate_limiter.can_create_custom_agent(user_id)
    
    if not can_create:
        logger.warning(f"Custom agent creation blocked - {message}", user_id=user_id)
        raise HTTPException(status_code=403, detail=message)
    
    # Validate input
    if len(request.name) < 2 or len(request.name) > 50:
        raise HTTPException(status_code=400, detail="Agent name must be 2-50 characters")
    
    if request.agent_type not in ["sharp", "insider", "degen", "bookie"]:
        raise HTTPException(status_code=400, detail="Invalid agent type")
    
    if len(request.personality_prompt) < 20:
        raise HTTPException(status_code=400, detail="Personality prompt too short")
    
    # Create agent
    agent_id = str(uuid.uuid4())
    agent = CustomAgent(
        id=agent_id,
        user_id=user_id,
        name=request.name,
        agent_type=request.agent_type,
        personality_prompt=request.personality_prompt,
        strategy_description=request.strategy_description,
        created_at=datetime.utcnow()
    )
    
    db.add(agent)
    
    # Update user's custom agent count
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.custom_agents_created += 1
    
    db.commit()
    
    logger.info(f"Custom agent created: {request.name}", user_id=user_id, agent_id=agent_id)
    
    return CustomAgentResponse(
        id=agent.id,
        name=agent.name,
        agent_type=agent.agent_type,
        version=agent.version,
        created_at=agent.created_at.isoformat(),
        roi=0.0,
        total_bets=0,
        win_rate=0.0
    )


@router.get("/custom/{agent_id}", response_model=CustomAgentResponse)
async def get_custom_agent(
    agent_id: str,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get a custom agent."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    agent = db.query(CustomAgent)\
        .filter(CustomAgent.id == agent_id, CustomAgent.user_id == user_id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return CustomAgentResponse(
        id=agent.id,
        name=agent.name,
        agent_type=agent.agent_type,
        version=agent.version,
        created_at=agent.created_at.isoformat(),
        roi=agent.roi,
        total_bets=agent.total_bets,
        win_rate=(agent.wins / agent.total_bets * 100) if agent.total_bets > 0 else 0
    )


@router.put("/custom/{agent_id}", response_model=CustomAgentResponse)
async def update_custom_agent(
    agent_id: str,
    request: CreateAgentRequest,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Update a custom agent."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    agent = db.query(CustomAgent)\
        .filter(CustomAgent.id == agent_id, CustomAgent.user_id == user_id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    agent.name = request.name
    agent.agent_type = request.agent_type
    agent.personality_prompt = request.personality_prompt
    agent.strategy_description = request.strategy_description
    agent.version += 1
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"Custom agent updated: {request.name}", user_id=user_id, agent_id=agent_id)
    
    return CustomAgentResponse(
        id=agent.id,
        name=agent.name,
        agent_type=agent.agent_type,
        version=agent.version,
        created_at=agent.created_at.isoformat(),
        roi=agent.roi,
        total_bets=agent.total_bets,
        win_rate=(agent.wins / agent.total_bets * 100) if agent.total_bets > 0 else 0
    )


@router.delete("/custom/{agent_id}")
async def delete_custom_agent(
    agent_id: str,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete a custom agent."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    agent = db.query(CustomAgent)\
        .filter(CustomAgent.id == agent_id, CustomAgent.user_id == user_id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(agent)
    db.commit()
    
    logger.info(f"Custom agent deleted: {agent.name}", user_id=user_id)
    
    return {"message": "Agent deleted"}
