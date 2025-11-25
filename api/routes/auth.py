"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from database.schema import get_db, User, UserTier
from database.auth import auth_manager
from monitoring.logger import logger

router = APIRouter()


class RegisterRequest(BaseModel):
    """User registration request."""
    email: str
    password: str


class LoginRequest(BaseModel):
    """User login request."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response with token."""
    access_token: str
    user_id: str
    email: str
    tier: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    tier: str
    created_at: str
    total_simulations: int


@router.post("/register", response_model=LoginResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    # Create user
    try:
        user = auth_manager.create_user(db, request.email, request.password, UserTier.FREE)
        
        # Generate token
        token = auth_manager.create_access_token(user.id)
        
        logger.info(f"New user registered: {request.email}", user_id=user.id)
        
        return LoginResponse(
            access_token=token,
            user_id=user.id,
            email=user.email,
            tier=user.tier.value
        )
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login user with email/password."""
    user = auth_manager.authenticate_user(db, request.email, request.password)
    
    if not user:
        logger.warning(f"Failed login attempt: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token = auth_manager.create_access_token(user.id)
    
    logger.info(f"User logged in: {request.email}", user_id=user.id)
    
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        tier=user.tier.value
    )


@router.post("/logout")
async def logout(user_id: str = None):
    """Logout user (client-side token deletion)."""
    if user_id:
        logger.info(f"User logged out", user_id=user_id)
    
    return {"message": "Logged out successfully"}


@router.get("/verify", response_model=UserResponse)
async def verify_token(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify token and return user info."""
    user_id = auth_manager.verify_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        tier=user.tier.value,
        created_at=user.created_at.isoformat(),
        total_simulations=user.total_simulations
    )
