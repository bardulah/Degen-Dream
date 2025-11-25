"""Real-time UI components for live simulation updates."""

import streamlit as st
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class AgentThinking:
    """Represents an agent's thinking during analysis."""
    agent_name: str
    agent_type: str
    decision: str  # "Pass", "Bet"
    bet_type: Optional[str] = None
    stake: Optional[float] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    timestamp: Optional[datetime] = None

    def display(self):
        """Display agent thinking in Streamlit."""
        emoji = {
            "sharp": "🧠",
            "insider": "🤫",
            "degen": "🎲",
            "bookie": "📊"
        }.get(self.agent_type, "")
        
        if self.decision == "Pass":
            st.info(f"{emoji} **{self.agent_name}** ({self.agent_type}): PASS")
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"{emoji} **{self.agent_name}** ({self.agent_type})")
                st.write(f"**{self.bet_type}**: €{self.stake:.2f} @ {self.confidence:.0f}% confidence")
                if self.reasoning:
                    st.caption(self.reasoning)
            with col2:
                st.metric("Stake", f"€{self.stake:.2f}")


class LiveGameAnalysis:
    """Container for live game analysis display."""

    def __init__(self, game_number: int, game_info: Dict[str, Any]):
        self.game_number = game_number
        self.game_info = game_info
        self.agent_thoughts: List[AgentThinking] = []
        self.debate_lines: List[str] = []
        self.consensus_bet: Optional[Dict[str, Any]] = None
        self.bet_result: Optional[Dict[str, Any]] = None
        self.current_bankroll: float = 0
        self.roi: float = 0

    def add_agent_thought(self, thought: AgentThinking):
        """Add agent thinking to display queue."""
        self.agent_thoughts.append(thought)

    def add_debate_line(self, speaker: str, statement: str):
        """Add debate statement."""
        self.debate_lines.append(f"**{speaker}**: {statement}")

    def set_consensus(self, bet: Dict[str, Any]):
        """Set the consensus bet."""
        self.consensus_bet = bet

    def set_result(self, result: Dict[str, Any]):
        """Set the bet result."""
        self.bet_result = result

    def display(self, show_debate: bool = False):
        """Render the live game analysis."""
        st.markdown(f"### 📊 Game {self.game_number}: {self.game_info.get('team1', '?')} vs {self.game_info.get('team2', '?')}")
        
        # Agent Analysis Section
        with st.container(border=True):
            st.write("🎰 **Agent Analysis**")
            
            # Display each agent's thinking
            for thought in self.agent_thoughts:
                thought.display()
        
        # Debate Section
        if show_debate and self.debate_lines:
            with st.expander("💬 Debate Transcript", expanded=False):
                for line in self.debate_lines:
                    st.write(line)
        
        # Consensus Bet
        if self.consensus_bet:
            with st.container(border=True):
                st.write("✅ **Consensus Bet**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Type",
                        self.consensus_bet.get('type', 'unknown')
                    )
                with col2:
                    st.metric(
                        "Stake",
                        f"€{self.consensus_bet.get('stake', 0):.2f}"
                    )
                with col3:
                    confidence = self.consensus_bet.get('confidence', 0)
                    st.metric(
                        "Confidence",
                        f"{confidence:.0f}%"
                    )
        
        # Bet Result
        if self.bet_result:
            result_type = self.bet_result.get('result', 'pending')
            if result_type == "win":
                st.success(f"✅ **WIN**: +€{self.bet_result.get('amount', 0):.2f}")
            elif result_type == "loss":
                st.error(f"❌ **LOSS**: -€{abs(self.bet_result.get('amount', 0)):.2f}")
            else:
                st.warning("⏳ Pending result...")
        
        # Bankroll Update
        if self.current_bankroll > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Current Bankroll", f"€{self.current_bankroll:.2f}")
            with col2:
                st.metric("ROI", f"{self.roi:+.2f}%")


class LiveBankrollTicker:
    """Live bankroll progression ticker."""

    def __init__(self, initial_bankroll: float):
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.history: List[Dict[str, Any]] = []

    def update(self, bankroll: float, game_num: int, roi: float, win_rate: float):
        """Update bankroll state."""
        self.current_bankroll = bankroll
        self.history.append({
            "game": game_num,
            "bankroll": bankroll,
            "roi": roi,
            "profit_loss": bankroll - self.initial_bankroll,
            "win_rate": win_rate
        })

    def display(self):
        """Display live ticker in Streamlit."""
        col1, col2, col3, col4 = st.columns(4)
        
        profit_loss = self.current_bankroll - self.initial_bankroll
        roi = (profit_loss / self.initial_bankroll) * 100 if self.initial_bankroll > 0 else 0
        
        with col1:
            st.metric(
                "Current Bankroll",
                f"€{self.current_bankroll:.2f}",
                f"{profit_loss:+.2f} EUR"
            )
        
        with col2:
            st.metric("ROI", f"{roi:+.2f}%")
        
        with col3:
            st.metric("Total Games", len(self.history))
        
        with col4:
            if self.history:
                latest = self.history[-1]
                st.metric("Win Rate", f"{latest['win_rate']:.1f}%")

    def display_chart(self):
        """Display bankroll progression chart."""
        if not self.history:
            st.info("No data yet")
            return
        
        df = pd.DataFrame(self.history)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.line_chart(df.set_index("game")[["bankroll"]], use_container_width=True)
        
        with col2:
            st.line_chart(df.set_index("game")[["roi"]], use_container_width=True)


class SimulationProgressBar:
    """Progress tracker for ongoing simulation."""

    def __init__(self, total_games: int):
        self.total_games = total_games
        self.completed_games = 0
        self.wins = 0
        self.losses = 0

    def update(self, won: bool):
        """Update progress."""
        self.completed_games += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1

    def display(self):
        """Display progress bar."""
        progress = self.completed_games / self.total_games if self.total_games > 0 else 0
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.progress(progress, text=f"Progress: {self.completed_games}/{self.total_games} games")
        
        with col2:
            st.write(f"W:{self.wins} L:{self.losses}")


class DebateViewer:
    """Display debate transcripts in an organized way."""

    def __init__(self):
        self.speakers: Dict[str, List[str]] = {}

    def add_statement(self, speaker: str, statement: str):
        """Add a debate statement."""
        if speaker not in self.speakers:
            self.speakers[speaker] = []
        self.speakers[speaker].append(statement)

    def display(self):
        """Render debate in expandable section."""
        if not self.speakers:
            return
        
        with st.expander("💬 Full Debate Transcript", expanded=False):
            for speaker, statements in self.speakers.items():
                with st.container(border=True):
                    st.write(f"**{speaker}**")
                    for stmt in statements:
                        st.write(f"_{stmt}_")

    def clear(self):
        """Clear all statements."""
        self.speakers.clear()


def create_agent_cards(agents_analysis: List[Dict[str, Any]]):
    """Create a grid of agent analysis cards.
    
    Args:
        agents_analysis: List of agent analysis dicts with name, type, decision, confidence
    """
    cols = st.columns(min(3, len(agents_analysis)))
    
    for idx, agent in enumerate(agents_analysis):
        with cols[idx % len(cols)]:
            decision = agent.get("decision", "PASS")
            decision_color = "green" if decision != "PASS" else "gray"
            
            st.write(f"""
            <div style="border: 2px solid {decision_color}; padding: 10px; border-radius: 5px;">
                <strong>{agent.get('name', 'Unknown')}</strong><br/>
                <small>{agent.get('type', 'unknown').upper()}</small><br/>
                <span style="color: {decision_color};"><strong>{decision}</strong></span>
                {f"<br/>💰 €{agent.get('stake', 0):.2f}" if agent.get('stake') else ""}
                {f"<br/>📊 {agent.get('confidence', 0):.0f}%" if agent.get('confidence') else ""}
            </div>
            """, unsafe_allow_html=True)
