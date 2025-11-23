"""Configuration settings for Bratislava Betting Syndicate."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration class."""

    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")

    # Agent Configuration
    NUM_SHARPS: int = int(os.getenv("NUM_SHARPS", "3"))
    NUM_INSIDERS: int = int(os.getenv("NUM_INSIDERS", "2"))
    NUM_DEGENS: int = int(os.getenv("NUM_DEGENS", "3"))
    NUM_BOOKIES: int = int(os.getenv("NUM_BOOKIES", "2"))

    # Simulation Settings
    STARTING_BANKROLL: float = float(os.getenv("STARTING_BANKROLL", "10000"))
    SIMULATION_GAMES: int = int(os.getenv("SIMULATION_GAMES", "100"))
    KELLY_FRACTION: float = float(os.getenv("KELLY_FRACTION", "0.25"))

    # Data Sources
    ODDS_API_BASE_URL: str = os.getenv(
        "ODDS_API_BASE_URL",
        "https://api.the-odds-api.com/v4"
    )
    NIKE_SCRAPER_ENABLED: bool = os.getenv("NIKE_SCRAPER_ENABLED", "true").lower() == "true"

    # Monetization
    PRO_SUBSCRIPTION_PRICE: float = float(os.getenv("PRO_SUBSCRIPTION_PRICE", "9.00"))
    CURRENCY: str = os.getenv("CURRENCY", "EUR")

    # GUI Settings
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))
    ENABLE_PYGAME_VISUALIZATION: bool = os.getenv(
        "ENABLE_PYGAME_VISUALIZATION", "true"
    ).lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bratislava_syndicate.log")

    # Agent Personalities
    AGENT_NAMES = {
        "sharps": ["Viktor", "Elena", "Boris"],
        "insiders": ["Nikolai", "Petra"],
        "degens": ["Jozef", "Marian", "Lucia"],
        "bookies": ["Tomáš", "Katarína"]
    }

    AGENT_PROMPTS = {
        "Viktor": "You're Viktor, a sharp bettor who only cares about expected value. You analyze Pinnacle closing lines and market efficiency. Never bet without a statistical edge.",
        "Elena": "You're Elena, a sharp bettor obsessed with closing line value. You track line movements and only bet when you can beat the closing number.",
        "Boris": "You're Boris, a sharp arbitrage specialist. You find market inefficiencies and exploit pricing errors across different sportsbooks.",
        "Nikolai": "You're Nikolai, an insider with connections at Niké betting. You claim to have inside information about fixed matches and injury news.",
        "Petra": "You're Petra, an insider who 'knows a guy' at every team. You're confident (sometimes overconfident) in your leaked information.",
        "Jozef": "You're Jozef, a degen bettor who lives for the thrill. You love massive parlays and betting on gut feelings. YOLO is your motto.",
        "Marian": "You're Marian, a superstitious degen who bases bets on horoscopes, lucky numbers, and random patterns. Logic is overrated.",
        "Lucia": "You're Lucia, a degen with simple rules: always bet home teams, always bet overs, and never trust favorites.",
        "Tomáš": "You're Tomáš, a bookie who manipulates lines to trap square bettors. You shade numbers and create traps.",
        "Katarína": "You're Katarína, a bookie focused on balancing books and maximizing juice. You predict where public money flows."
    }

    @classmethod
    def validate(cls) -> bool:
        """Validate required settings."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")
        return True


settings = Settings()
