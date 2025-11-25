"""Structured logging system for debugging and analytics."""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import os

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class StructuredJSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add custom fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "simulation_id"):
            log_data["simulation_id"] = record.simulation_id
        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # Include exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class AppLogger:
    """Application logger with structured JSON output."""

    def __init__(self, name: str = "bratislava_betting_syndicate"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # File handler - JSON format
        json_handler = logging.FileHandler(LOGS_DIR / "app.json.log")
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(StructuredJSONFormatter())
        self.logger.addHandler(json_handler)

        # File handler - readable format
        text_handler = logging.FileHandler(LOGS_DIR / "app.log")
        text_handler.setLevel(logging.INFO)
        text_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        text_handler.setFormatter(text_formatter)
        self.logger.addHandler(text_handler)

        # Console handler for development
        if os.getenv("DEBUG") == "true":
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(text_formatter)
            self.logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log("debug", message, kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log("info", message, kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log("warning", message, kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self._log("error", message, kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self._log("critical", message, kwargs)

    def _log(self, level: str, message: str, context: Dict[str, Any]) -> None:
        """Log message with context."""
        log_func = getattr(self.logger, level)
        
        # Create a LogRecord with custom fields
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            "(unknown file)",
            0,
            message,
            (),
            None
        )
        
        # Add context fields
        for key, value in context.items():
            setattr(record, key, value)
        
        log_func(message, extra=context)

    def log_simulation_start(self, user_id: str, simulation_id: str, num_games: int, sport: str) -> None:
        """Log simulation start."""
        self.info(
            f"Simulation started: {num_games} {sport} games",
            user_id=user_id,
            simulation_id=simulation_id,
            num_games=num_games,
            sport=sport
        )

    def log_simulation_end(self, user_id: str, simulation_id: str, roi: float = None, win_rate: float = None) -> None:
        """Log simulation completion."""
        if roi is not None and win_rate is not None:
            msg = f"Simulation completed: ROI {roi:.2f}%, Win Rate {win_rate:.1f}%"
        else:
            msg = "Simulation analysis completed (results pending)"
        
        self.info(
            msg,
            user_id=user_id,
            simulation_id=simulation_id,
            roi=roi,
            win_rate=win_rate
        )

    def log_agent_decision(self, agent_name: str, simulation_id: str, decision: str, confidence: float) -> None:
        """Log agent decision."""
        self.debug(
            f"Agent decision: {agent_name}",
            simulation_id=simulation_id,
            agent_name=agent_name,
            decision=decision,
            confidence=confidence
        )

    def log_bet_placed(self, simulation_id: str, agent_name: str, team: str, stake: float, odds: float) -> None:
        """Log bet placement."""
        self.info(
            f"Bet placed: {agent_name} on {team}",
            simulation_id=simulation_id,
            agent_name=agent_name,
            team=team,
            stake=stake,
            odds=odds
        )

    def log_bet_result(self, simulation_id: str, won: bool, profit_loss: float) -> None:
        """Log bet result."""
        result = "WON" if won else "LOST"
        self.info(
            f"Bet {result}: {profit_loss:+.2f}",
            simulation_id=simulation_id,
            won=won,
            profit_loss=profit_loss
        )

    def log_api_error(self, endpoint: str, error: str, user_id: Optional[str] = None) -> None:
        """Log API error."""
        self.error(
            f"API error at {endpoint}: {error}",
            user_id=user_id,
            endpoint=endpoint
        )

    def log_llm_call(self, agent_name: str, model: str, tokens_used: int, cost: float) -> None:
        """Log LLM API call."""
        self.debug(
            f"LLM call: {agent_name} using {model}",
            agent_name=agent_name,
            model=model,
            tokens=tokens_used,
            cost=cost
        )

    def log_rate_limit_exceeded(self, user_id: str, limit_type: str) -> None:
        """Log rate limit exceeded."""
        self.warning(
            f"Rate limit exceeded: {limit_type}",
            user_id=user_id,
            limit_type=limit_type
        )


# Global logger instance
logger = AppLogger()
