"""Subscription and billing routes."""

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import stripe
import os
from datetime import datetime, timedelta

from database.schema import get_db, User, UserTier, UsageLimit
from database.auth import auth_manager
from monitoring.logger import logger

router = APIRouter()

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_")


class UpgradeTierRequest(BaseModel):
    """Upgrade tier request."""
    tier: str  # "pro" or "enterprise"


class SubscriptionInfo(BaseModel):
    """Subscription information."""
    tier: str
    active: bool
    stripe_customer_id: Optional[str]
    subscription_end_date: Optional[str]
    auto_renew: bool


class UsageLimitInfo(BaseModel):
    """Usage limit info for tier."""
    simulations_per_day: int
    max_games_per_sim: int
    custom_agents_allowed: int
    api_calls_per_month: int
    features: dict


@router.get("/info", response_model=SubscriptionInfo)
async def get_subscription_info(
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get user's subscription info."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return SubscriptionInfo(
        tier=user.tier.value,
        active=user.is_active,
        stripe_customer_id=user.stripe_customer_id,
        subscription_end_date=user.subscription_end_date.isoformat() if user.subscription_end_date else None,
        auto_renew=user.subscription_auto_renew
    )


@router.get("/limits/{tier}", response_model=UsageLimitInfo)
async def get_tier_limits(
    tier: str,
    db: Session = Depends(get_db)
):
    """Get usage limits for a tier."""
    try:
        tier_enum = UserTier[tier.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    limit = db.query(UsageLimit).filter(UsageLimit.tier == tier_enum).first()
    if not limit:
        raise HTTPException(status_code=404, detail="Tier limits not configured")
    
    return UsageLimitInfo(
        simulations_per_day=limit.simulations_per_day,
        max_games_per_sim=limit.max_games_per_sim,
        custom_agents_allowed=limit.custom_agents_allowed,
        api_calls_per_month=limit.api_calls_per_month,
        features=limit.features
    )


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: UpgradeTierRequest,
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for tier upgrade."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Map tiers to Stripe price IDs
    price_ids = {
        "pro": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_pro_monthly"),
        "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE_MONTHLY", "price_enterprise_monthly")
    }
    
    if request.tier not in price_ids:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    try:
        # Create or get Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": user.id}
            )
            user.stripe_customer_id = customer.id
            db.commit()
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_ids[request.tier],
                    "quantity": 1
                }
            ],
            mode="subscription",
            success_url=os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/success"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/cancel"),
            metadata={
                "user_id": user.id,
                "tier": request.tier
            }
        )
        
        logger.info(f"Checkout session created", user_id=user_id, tier=request.tier)
        
        return {"checkout_url": session.url}
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}", user_id=user_id)
        raise HTTPException(status_code=500, detail="Billing error")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhooks."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle subscription events
    if event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]
        
        # Find user
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.stripe_subscription_id = subscription["id"]
            user.subscription_end_date = datetime.fromtimestamp(subscription["current_period_end"])
            db.commit()
            logger.info(f"Subscription updated", user_id=user.id)
    
    elif event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("user_id")
        new_tier = session["metadata"].get("tier")
        
        if user_id and new_tier:
            # Upgrade user tier
            try:
                tier_enum = UserTier[new_tier.upper()]
                auth_manager.upgrade_tier(db, user_id, tier_enum, session["subscription"])
                logger.info(f"User upgraded to {new_tier}", user_id=user_id)
            except Exception as e:
                logger.error(f"Upgrade failed: {str(e)}", user_id=user_id)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]
        
        # Find user and downgrade to free
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.tier = UserTier.FREE
            user.subscription_end_date = None
            db.commit()
            logger.info(f"Subscription cancelled - downgraded to free", user_id=user.id)
    
    return {"status": "success"}


@router.post("/cancel-subscription")
async def cancel_subscription(
    user_id: str = Header(None),
    db: Session = Depends(get_db)
):
    """Cancel user's subscription."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    
    try:
        stripe.Subscription.delete(user.stripe_subscription_id)
        
        user.tier = UserTier.FREE
        user.stripe_subscription_id = None
        user.subscription_end_date = None
        db.commit()
        
        logger.info(f"Subscription cancelled", user_id=user_id)
        
        return {"message": "Subscription cancelled"}
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}", user_id=user_id)
        raise HTTPException(status_code=500, detail="Cancellation failed")
