"""Subscription management for pro tier features."""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json


class SubscriptionTier(Enum):
    """Subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class Subscription:
    """User subscription details."""
    user_id: str
    tier: SubscriptionTier
    start_date: datetime
    end_date: Optional[datetime]
    auto_renew: bool
    price_paid: float
    currency: str = "EUR"


class SubscriptionManager:
    """Manages user subscriptions and feature access."""

    FEATURE_LIMITS = {
        SubscriptionTier.FREE: {
            "max_simulations_per_day": 3,
            "max_games_per_simulation": 100,
            "custom_agents": False,
            "api_access": False,
            "historical_backtesting": False,
            "pdf_exports": False,
            "advanced_analytics": False,
            "priority_support": False,
            "max_agents": 10,  # Default 10 agents
        },
        SubscriptionTier.PRO: {
            "max_simulations_per_day": 50,
            "max_games_per_simulation": 1000,
            "custom_agents": True,
            "api_access": True,
            "historical_backtesting": True,
            "pdf_exports": True,
            "advanced_analytics": True,
            "priority_support": True,
            "max_agents": 50,  # Up to 50 custom agents
        },
        SubscriptionTier.ENTERPRISE: {
            "max_simulations_per_day": 999999,
            "max_games_per_simulation": 999999,
            "custom_agents": True,
            "api_access": True,
            "historical_backtesting": True,
            "pdf_exports": True,
            "advanced_analytics": True,
            "priority_support": True,
            "max_agents": 999,
            "white_label": True,
            "dedicated_support": True,
        }
    }

    PRICING = {
        SubscriptionTier.FREE: 0.00,
        SubscriptionTier.PRO: 9.00,  # €9/month
        SubscriptionTier.ENTERPRISE: 99.00,  # €99/month
    }

    def __init__(self):
        """Initialize subscription manager."""
        self.subscriptions: Dict[str, Subscription] = {}

    def create_subscription(
        self,
        user_id: str,
        tier: SubscriptionTier,
        duration_months: int = 1,
        auto_renew: bool = True
    ) -> Subscription:
        """Create a new subscription.

        Args:
            user_id: User identifier
            tier: Subscription tier
            duration_months: Subscription duration in months
            auto_renew: Whether to auto-renew

        Returns:
            Subscription object
        """
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30 * duration_months)
        price = self.PRICING[tier] * duration_months

        subscription = Subscription(
            user_id=user_id,
            tier=tier,
            start_date=start_date,
            end_date=end_date,
            auto_renew=auto_renew,
            price_paid=price
        )

        self.subscriptions[user_id] = subscription
        return subscription

    def check_feature_access(
        self,
        user_id: str,
        feature: str
    ) -> bool:
        """Check if user has access to a feature.

        Args:
            user_id: User identifier
            feature: Feature name

        Returns:
            True if user has access, False otherwise
        """
        subscription = self.subscriptions.get(user_id)

        if not subscription:
            # Default to free tier
            tier = SubscriptionTier.FREE
        elif not self.is_subscription_active(user_id):
            # Expired subscription defaults to free
            tier = SubscriptionTier.FREE
        else:
            tier = subscription.tier

        limits = self.FEATURE_LIMITS[tier]
        return limits.get(feature, False)

    def get_feature_limit(
        self,
        user_id: str,
        feature: str
    ) -> Any:
        """Get the limit for a specific feature.

        Args:
            user_id: User identifier
            feature: Feature name

        Returns:
            Feature limit value
        """
        subscription = self.subscriptions.get(user_id)

        if not subscription or not self.is_subscription_active(user_id):
            tier = SubscriptionTier.FREE
        else:
            tier = subscription.tier

        limits = self.FEATURE_LIMITS[tier]
        return limits.get(feature, 0)

    def is_subscription_active(self, user_id: str) -> bool:
        """Check if subscription is active.

        Args:
            user_id: User identifier

        Returns:
            True if active, False otherwise
        """
        subscription = self.subscriptions.get(user_id)

        if not subscription:
            return False

        if subscription.end_date and datetime.now() > subscription.end_date:
            return False

        return True

    def upgrade_subscription(
        self,
        user_id: str,
        new_tier: SubscriptionTier
    ) -> Subscription:
        """Upgrade a user's subscription.

        Args:
            user_id: User identifier
            new_tier: New subscription tier

        Returns:
            Updated subscription
        """
        existing = self.subscriptions.get(user_id)

        if existing:
            # Calculate prorated refund/charge
            # In production, this would integrate with Stripe
            pass

        return self.create_subscription(user_id, new_tier)

    def cancel_subscription(self, user_id: str):
        """Cancel a subscription (end of current period).

        Args:
            user_id: User identifier
        """
        subscription = self.subscriptions.get(user_id)

        if subscription:
            subscription.auto_renew = False

    def get_pricing_info(self) -> Dict[str, Any]:
        """Get pricing information for all tiers.

        Returns:
            Pricing and features by tier
        """
        return {
            "tiers": [
                {
                    "name": "Free",
                    "price": 0,
                    "currency": "EUR",
                    "features": [
                        "3 simulations per day",
                        "Up to 100 games per simulation",
                        "10 pre-built agents",
                        "Basic analytics",
                        "Community support"
                    ]
                },
                {
                    "name": "Pro",
                    "price": 9,
                    "currency": "EUR",
                    "period": "month",
                    "features": [
                        "50 simulations per day",
                        "Up to 1,000 games per simulation",
                        "Custom agents (up to 50)",
                        "Historical backtesting",
                        "PDF exports",
                        "Advanced analytics",
                        "API access",
                        "Priority support"
                    ],
                    "popular": True
                },
                {
                    "name": "Enterprise",
                    "price": 99,
                    "currency": "EUR",
                    "period": "month",
                    "features": [
                        "Unlimited simulations",
                        "Unlimited games",
                        "Unlimited custom agents",
                        "White-label options",
                        "Dedicated support",
                        "Custom integrations",
                        "On-premise deployment"
                    ]
                }
            ]
        }


class FeatureGate:
    """Decorator for gating features behind subscription tiers."""

    def __init__(self, feature: str, subscription_manager: SubscriptionManager):
        """Initialize feature gate.

        Args:
            feature: Feature name to check
            subscription_manager: SubscriptionManager instance
        """
        self.feature = feature
        self.subscription_manager = subscription_manager

    def __call__(self, func):
        """Wrap function with feature check."""
        def wrapper(user_id: str, *args, **kwargs):
            if not self.subscription_manager.check_feature_access(user_id, self.feature):
                raise PermissionError(
                    f"Feature '{self.feature}' requires a Pro subscription. "
                    f"Upgrade at https://bratislava-syndicate.com/pricing"
                )
            return func(user_id, *args, **kwargs)

        return wrapper


# Example usage functions
def create_stripe_checkout_session(tier: SubscriptionTier) -> str:
    """Create Stripe checkout session (placeholder).

    Args:
        tier: Subscription tier

    Returns:
        Checkout session URL
    """
    # In production, integrate with Stripe:
    # import stripe
    # stripe.api_key = settings.STRIPE_API_KEY
    # session = stripe.checkout.Session.create(...)

    return f"https://checkout.stripe.com/pay/pro-{tier.value}"


def handle_stripe_webhook(event_type: str, data: Dict[str, Any]):
    """Handle Stripe webhook events (placeholder).

    Args:
        event_type: Stripe event type
        data: Event data
    """
    # Handle events like:
    # - checkout.session.completed
    # - customer.subscription.updated
    # - customer.subscription.deleted
    # - invoice.payment_succeeded
    # - invoice.payment_failed

    if event_type == "checkout.session.completed":
        # Create subscription in database
        pass
    elif event_type == "customer.subscription.deleted":
        # Cancel subscription
        pass
