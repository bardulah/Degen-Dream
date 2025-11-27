"""Database schema and models for Bratislava Betting Syndicate."""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum
import os

# Database URL (SQLite for dev, PostgreSQL for prod)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bratislava.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserTier(str, enum.Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class BetType(str, enum.Enum):
    """Types of bets."""
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    PARLAY = "parlay"





class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)  # UUID
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)  # bcrypt hash
    tier = Column(SQLEnum(UserTier), default=UserTier.FREE, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    api_key = Column(String, unique=True, nullable=True, index=True)  # For API access

    # Subscription details
    stripe_customer_id = Column(String, nullable=True, unique=True)
    stripe_subscription_id = Column(String, nullable=True, unique=True)
    subscription_end_date = Column(DateTime, nullable=True)
    subscription_auto_renew = Column(Boolean, default=True)

    # Usage tracking
    simulations_run_today = Column(Integer, default=0)
    total_simulations = Column(Integer, default=0)
    custom_agents_created = Column(Integer, default=0)
    api_calls_this_month = Column(Integer, default=0)

    # Relationships
    simulations = relationship("Simulation", back_populates="user", cascade="all, delete-orphan")
    custom_agents = relationship("CustomAgent", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.tier.value})>"


class Simulation(Base):
    """Simulation run record."""
    __tablename__ = "simulations"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(String, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Simulation parameters
    num_games = Column(Integer)
    starting_bankroll = Column(Float)
    kelly_fraction = Column(Float)
    sport = Column(String)
    use_live_data = Column(Boolean, default=False)

    # Results (populated after real results come in)
    total_bets = Column(Integer, nullable=True)
    total_wagered = Column(Float, nullable=True)
    roi = Column(Float, nullable=True)  # Overall ROI
    win_rate = Column(Float, nullable=True)  # Overall win rate
    profit = Column(Float, nullable=True)  # Total profit/loss
    final_bankroll = Column(Float, nullable=True)  # Ending bankroll

    # Result tracking
    bets_settled = Column(Integer, default=0)  # How many bets have results
    last_result_check = Column(DateTime, nullable=True)  # Last time we checked for results

    # Metadata
    duration_seconds = Column(Integer, nullable=True)  # Execution time
    status = Column(String, default="completed")  # completed, in_progress, failed, awaiting_results
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Checkpoint data (for resumable sims)
    checkpoint_games_completed = Column(Integer, default=0)
    checkpoint_state = Column(JSON, nullable=True)  # Serialized state for resume

    # Relationships
    user = relationship("User", back_populates="simulations")
    bets = relationship("Bet", back_populates="simulation", cascade="all, delete-orphan")
    agent_stats = relationship("AgentSimulationStats", back_populates="simulation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        roi_str = f"{self.roi:.2f}%" if self.roi is not None else "N/A"
        return f"<Simulation {self.id} - ROI: {roi_str}>"


class Bet(Base):
    """Individual bet record."""
    __tablename__ = "bets"

    id = Column(String, primary_key=True, index=True)  # UUID
    simulation_id = Column(String, ForeignKey("simulations.id"), index=True)
    agent_name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Bet details
    game_home_team = Column(String)
    game_away_team = Column(String)
    sport = Column(String)
    bet_team = Column(String)
    bet_type = Column(SQLEnum(BetType))
    line = Column(Float)
    odds = Column(Float)
    stake = Column(Float)
    confidence = Column(Float)  # 0.0-1.0

    # Match result tracking (populated after game finishes)
    game_date = Column(String, nullable=True)  # YYYYMMDD format for ESPN API
    game_id_espn = Column(String, nullable=True, index=True)  # ESPN game ID
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    actual_winner = Column(String, nullable=True)  # Team name or "TIE"
    result_status = Column(String, nullable=True)  # "pending", "won", "lost", "push"
    result_fetched_at = Column(DateTime, nullable=True)
    profit_loss = Column(Float, nullable=True)  # Actual P&L after result

    # Closing Line Value (CLV) tracking
    closing_odds = Column(Float, nullable=True)  # Odds at game time (closing line)
    clv_percentage = Column(Float, nullable=True)  # (closing_odds - bet_odds) / bet_odds * 100
    beat_closing_line = Column(Boolean, nullable=True)  # True if bet odds > closing odds

    # Metadata
    reasoning = Column(Text)
    edge_estimate = Column(Float, nullable=True)
    kelly_percentage = Column(Float, nullable=True)

    # Relationships
    simulation = relationship("Simulation", back_populates="bets")

    def __repr__(self) -> str:
        return f"<Bet {self.id} - {self.bet_team} {self.bet_type} @{self.odds}>"


class CustomAgent(Base):
    """User-created custom agent (Pro+ feature)."""
    __tablename__ = "custom_agents"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(String, ForeignKey("users.id"), index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Agent configuration
    agent_type = Column(String)  # sharp, insider, degen, bookie
    personality_prompt = Column(Text)
    strategy_description = Column(Text)
    
    # Performance tracking
    total_bets = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    roi = Column(Float, default=0.0)
    
    # Versioning
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="custom_agents")

    def __repr__(self) -> str:
        return f"<CustomAgent {self.name} v{self.version}>"


class AgentSimulationStats(Base):
    """Per-agent statistics for a simulation."""
    __tablename__ = "agent_simulation_stats"

    id = Column(String, primary_key=True, index=True)
    simulation_id = Column(String, ForeignKey("simulations.id"), index=True)
    agent_name = Column(String, index=True)
    agent_type = Column(String)
    
    # Performance in this simulation
    initial_bankroll = Column(Float)
    final_bankroll = Column(Float)
    roi = Column(Float)
    total_bets = Column(Integer)
    wins = Column(Integer)
    losses = Column(Integer)
    win_rate = Column(Float)
    profit_loss = Column(Float)
    
    # Relationships
    simulation = relationship("Simulation", back_populates="agent_stats")

    def __repr__(self) -> str:
        return f"<AgentStats {self.agent_name} - ROI: {self.roi:.2f}%>"


class AuditLog(Base):
    """Audit trail for compliance and debugging."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # What happened
    event_type = Column(String, index=True)  # simulation_started, agent_created, tier_upgraded, etc.
    resource_type = Column(String, nullable=True)  # user, simulation, agent, etc.
    resource_id = Column(String, nullable=True, index=True)
    
    # Details
    action = Column(String)  # create, update, delete, login, logout
    details = Column(JSON)  # Additional context
    ip_address = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.event_type} - {self.resource_type}:{self.resource_id}>"


class UsageLimit(Base):
    """Rate limits and usage quotas by tier."""
    __tablename__ = "usage_limits"

    tier = Column(SQLEnum(UserTier), primary_key=True)
    simulations_per_day = Column(Integer)
    max_games_per_sim = Column(Integer)
    custom_agents_allowed = Column(Integer)
    api_calls_per_month = Column(Integer)
    features = Column(JSON)  # {custom_agents: True, pdf_export: True, api_access: False, ...}


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    
    # Populate usage limits if not exists
    session = SessionLocal()
    if session.query(UsageLimit).count() == 0:
        limits = [
            UsageLimit(
                tier=UserTier.FREE,
                simulations_per_day=3,
                max_games_per_sim=100,
                custom_agents_allowed=0,
                api_calls_per_month=0,
                features={
                    "custom_agents": False,
                    "pdf_export": False,
                    "api_access": False,
                    "backtesting": False,
                    "priority_support": False
                }
            ),
            UsageLimit(
                tier=UserTier.PRO,
                simulations_per_day=50,
                max_games_per_sim=1000,
                custom_agents_allowed=50,
                api_calls_per_month=10000,
                features={
                    "custom_agents": True,
                    "pdf_export": True,
                    "api_access": True,
                    "backtesting": True,
                    "priority_support": True
                }
            ),
            UsageLimit(
                tier=UserTier.ENTERPRISE,
                simulations_per_day=999999,
                max_games_per_sim=999999,
                custom_agents_allowed=999999,
                api_calls_per_month=999999,
                features={
                    "custom_agents": True,
                    "pdf_export": True,
                    "api_access": True,
                    "backtesting": True,
                    "priority_support": True,
                    "white_label": True,
                    "dedicated_support": True,
                    "on_premise": True
                }
            )
        ]
        for limit in limits:
            session.add(limit)
        session.commit()
    session.close()


def get_db():
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
