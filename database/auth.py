"""Authentication and authorization utilities."""

import uuid
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets
from sqlalchemy.orm import Session
from database.schema import User, UserTier, UsageLimit, AuditLog
import os

# For production, use python-jose + passlib
try:
    import jwt
    import bcrypt
except ImportError:
    print("Warning: jwt or bcrypt not installed. Install with: pip install pyjwt bcrypt")


class AuthManager:
    """Handle user authentication and authorization."""

    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
        self.algorithm = "HS256"
        self.token_expire_hours = 24

    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        try:
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except:
            # Fallback to simple hash if bcrypt not available
            return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except:
            # Fallback
            return hashlib.sha256(password.encode()).hexdigest() == password_hash

    def create_user(
        self,
        db: Session,
        email: str,
        password: str,
        tier: UserTier = UserTier.FREE
    ) -> User:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        password_hash = self.hash_password(password)
        api_key = self.generate_api_key()

        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            tier=tier,
            api_key=api_key,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Log creation
        self._log_event(db, None, "user_created", "user", user_id, "create", {"email": email})

        return user

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email/password."""
        user = db.query(User).filter(User.email == email).first()
        if not user or not self.verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        # Log login
        self._log_event(db, user.id, "login_success", "user", user.id, "login")

        return user

    def create_access_token(self, user_id: str) -> str:
        """Create JWT token."""
        try:
            payload = {
                "user_id": user_id,
                "exp": datetime.utcnow() + timedelta(hours=self.token_expire_hours),
                "iat": datetime.utcnow()
            }
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        except:
            return None

    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user_id."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload.get("user_id")
        except:
            return None

    def generate_api_key(self) -> str:
        """Generate a random API key."""
        return f"bbsyn_{secrets.token_urlsafe(32)}"

    def get_user_tier(self, db: Session, user_id: str) -> Optional[UserTier]:
        """Get user's current tier."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Check if subscription expired
        if user.subscription_end_date and user.subscription_end_date < datetime.utcnow():
            if not user.subscription_auto_renew:
                user.tier = UserTier.FREE
                db.commit()

        return user.tier

    def upgrade_tier(self, db: Session, user_id: str, new_tier: UserTier, stripe_subscription_id: str = None) -> bool:
        """Upgrade user tier (called by Stripe webhook)."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        old_tier = user.tier
        user.tier = new_tier
        
        if stripe_subscription_id:
            user.stripe_subscription_id = stripe_subscription_id
            user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
            user.subscription_auto_renew = True

        db.commit()

        # Log upgrade
        self._log_event(db, user_id, "tier_upgraded", "user", user_id, "update", 
                       {"old_tier": old_tier.value, "new_tier": new_tier.value})

        return True

    def reset_daily_limits(self, db: Session, user_id: str) -> None:
        """Reset daily usage limits (call via scheduler)."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.simulations_run_today = 0
            db.commit()

    def _log_event(self, db: Session, user_id: str, event_type: str, resource_type: str, 
                   resource_id: str, action: str, details: dict = None) -> None:
        """Log audit event."""
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {}
        )
        db.add(log)
        db.commit()


class RateLimiter:
    """Enforce rate limits based on tier."""

    def __init__(self, db: Session, auth_manager: AuthManager):
        self.db = db
        self.auth_manager = auth_manager

    def can_run_simulation(self, user_id: str) -> tuple[bool, str]:
        """Check if user can run a simulation."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        tier = self.auth_manager.get_user_tier(self.db, user_id)
        limit = self.db.query(UsageLimit).filter(UsageLimit.tier == tier).first()

        if not limit:
            return False, "Usage limits not configured"

        # Check daily limit
        if user.simulations_run_today >= limit.simulations_per_day:
            reset_time = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M UTC")
            return False, f"Daily limit reached ({limit.simulations_per_day}/day). Resets at {reset_time}"

        return True, ""

    def can_create_custom_agent(self, user_id: str) -> tuple[bool, str]:
        """Check if user can create a custom agent."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"

        tier = self.auth_manager.get_user_tier(self.db, user_id)
        limit = self.db.query(UsageLimit).filter(UsageLimit.tier == tier).first()

        if not limit or not limit.features.get("custom_agents"):
            return False, f"Custom agents not available in {tier.value.upper()} tier. Upgrade to Pro"

        if user.custom_agents_created >= limit.custom_agents_allowed:
            return False, f"Custom agent limit reached ({limit.custom_agents_allowed})"

        return True, ""

    def can_export_pdf(self, user_id: str) -> tuple[bool, str]:
        """Check if user can export PDF reports."""
        tier = self.auth_manager.get_user_tier(self.db, user_id)
        limit = self.db.query(UsageLimit).filter(UsageLimit.tier == tier).first()

        if not limit or not limit.features.get("pdf_export"):
            return False, f"PDF export not available in {tier.value.upper()} tier. Upgrade to Pro"

        return True, ""

    def can_use_api(self, user_id: str) -> tuple[bool, str]:
        """Check if user can use API."""
        tier = self.auth_manager.get_user_tier(self.db, user_id)
        limit = self.db.query(UsageLimit).filter(UsageLimit.tier == tier).first()

        if not limit or not limit.features.get("api_access"):
            return False, f"API access not available in {tier.value.upper()} tier. Upgrade to Pro"

        return True, ""

    def record_api_call(self, user_id: str) -> None:
        """Record an API call for monthly quota tracking."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.api_calls_this_month += 1
            self.db.commit()

    def record_simulation(self, user_id: str) -> None:
        """Record a simulation run."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.simulations_run_today += 1
            user.total_simulations += 1
            self.db.commit()


# Global instances
auth_manager = AuthManager()
