"""Event emission system for real-time simulation updates."""

from typing import Callable, Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class SimulationEventType(Enum):
    """Types of simulation events."""
    GAME_START = "game_start"
    AGENT_ANALYSIS = "agent_analysis"
    DEBATE_START = "debate_start"
    DEBATE_STATEMENT = "debate_statement"
    DEBATE_END = "debate_end"
    CONSENSUS_BET = "consensus_bet"
    BET_PLACED = "bet_placed"
    BET_RESULT = "bet_result"
    BANKROLL_UPDATE = "bankroll_update"
    GAME_END = "game_end"
    SIMULATION_COMPLETE = "simulation_complete"
    ERROR = "error"


@dataclass
class SimulationEvent:
    """A simulation event."""
    type: SimulationEventType
    timestamp: datetime
    game_number: int
    data: Dict[str, Any]


class SimulationEventEmitter:
    """Emits events during simulation for real-time UI updates."""

    def __init__(self):
        self.callbacks: Dict[SimulationEventType, List[Callable]] = {}
        self.event_history: List[SimulationEvent] = []

    def on(self, event_type: SimulationEventType, callback: Callable):
        """Register a callback for an event type.
        
        Args:
            event_type: The event type to listen for
            callback: Function to call when event occurs (receives SimulationEvent)
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    def emit(self, event_type: SimulationEventType, game_number: int = 0, data: Optional[Dict[str, Any]] = None):
        """Emit an event.
        
        Args:
            event_type: The event type
            game_number: Current game number
            data: Event-specific data
        """
        data = data or {}
        event = SimulationEvent(
            type=event_type,
            timestamp=datetime.utcnow(),
            game_number=game_number,
            data=data
        )
        
        # Store in history
        self.event_history.append(event)
        
        # Call registered callbacks
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event callback for {event_type}: {e}")

    def clear_history(self):
        """Clear event history."""
        self.event_history.clear()

    def get_events_for_game(self, game_number: int) -> List[SimulationEvent]:
        """Get all events for a specific game."""
        return [e for e in self.event_history if e.game_number == game_number]

    def get_last_event(self, event_type: Optional[SimulationEventType] = None) -> Optional[SimulationEvent]:
        """Get the last event, optionally filtered by type."""
        if not self.event_history:
            return None
        
        if event_type is None:
            return self.event_history[-1]
        
        for event in reversed(self.event_history):
            if event.type == event_type:
                return event
        
        return None


# Global emitter instance
event_emitter = SimulationEventEmitter()


def reset_emitter():
    """Reset the global event emitter."""
    global event_emitter
    event_emitter = SimulationEventEmitter()
