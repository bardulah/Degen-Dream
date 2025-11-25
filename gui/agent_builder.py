"""Custom Agent Builder UI for creating and testing custom agents."""

import streamlit as st
from typing import Dict, Any, Optional
from dataclasses import dataclass
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from database.schema import SessionLocal, CustomAgent, User
from agents.base_agent import AgentType
from config.settings import settings


@dataclass
class CustomAgentConfig:
    """Configuration for a custom agent."""
    name: str
    agent_type: str  # "sharp", "insider", "degen", "bookie"
    personality: str  # Custom personality prompt
    risk_tolerance: float  # 0.0 - 1.0
    confidence_threshold: float  # Minimum confidence to place bet
    max_bet_size: float  # Max EUR per bet
    description: str


class CustomAgentBuilder:
    """Builder for creating custom agents."""

    def __init__(self):
        self.db = SessionLocal()

    def create_agent(
        self,
        user_id: str,
        config: CustomAgentConfig
    ) -> Optional[CustomAgent]:
        """Create a custom agent.
        
        Args:
            user_id: Owner user ID
            config: Agent configuration
            
        Returns:
            Created CustomAgent or None if error
        """
        try:
            agent = CustomAgent(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=config.name,
                agent_type=config.agent_type,
                personality_prompt=config.personality,
                risk_tolerance=config.risk_tolerance,
                confidence_threshold=config.confidence_threshold,
                max_bet_size=config.max_bet_size,
                description=config.description,
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            self.db.add(agent)
            self.db.commit()
            
            return agent
        except Exception as e:
            st.error(f"Failed to create agent: {str(e)}")
            self.db.rollback()
            return None

    def update_agent(
        self,
        agent_id: str,
        config: CustomAgentConfig
    ) -> Optional[CustomAgent]:
        """Update an existing agent.
        
        Args:
            agent_id: Agent ID to update
            config: New configuration
            
        Returns:
            Updated agent or None if error
        """
        try:
            agent = self.db.query(CustomAgent).filter(
                CustomAgent.id == agent_id
            ).first()
            
            if not agent:
                st.error("Agent not found")
                return None
            
            agent.name = config.name
            agent.agent_type = config.agent_type
            agent.personality_prompt = config.personality
            agent.risk_tolerance = config.risk_tolerance
            agent.confidence_threshold = config.confidence_threshold
            agent.max_bet_size = config.max_bet_size
            agent.description = config.description
            
            self.db.commit()
            return agent
        except Exception as e:
            st.error(f"Failed to update agent: {str(e)}")
            self.db.rollback()
            return None

    def delete_agent(self, agent_id: str) -> bool:
        """Delete a custom agent.
        
        Args:
            agent_id: Agent ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            agent = self.db.query(CustomAgent).filter(
                CustomAgent.id == agent_id
            ).first()
            
            if agent:
                self.db.delete(agent)
                self.db.commit()
                return True
            return False
        except Exception as e:
            st.error(f"Failed to delete agent: {str(e)}")
            self.db.rollback()
            return False

    def get_agents(self, user_id: str) -> list[CustomAgent]:
        """Get all agents for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of CustomAgent objects
        """
        return self.db.query(CustomAgent).filter(
            CustomAgent.user_id == user_id
        ).all()

    def get_agent(self, agent_id: str) -> Optional[CustomAgent]:
        """Get a specific agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            CustomAgent or None
        """
        return self.db.query(CustomAgent).filter(
            CustomAgent.id == agent_id
        ).first()

    def __del__(self):
        """Cleanup database connection."""
        self.db.close()


def render_agent_builder_ui():
    """Render the custom agent builder UI in Streamlit."""
    st.header("🎭 Custom Agent Builder")
    
    tabs = st.tabs(["Create New", "Manage Existing", "Agent Gallery", "Test Agent"])
    
    with tabs[0]:
        render_create_agent_tab()
    
    with tabs[1]:
        render_manage_agents_tab()
    
    with tabs[2]:
        render_agent_gallery_tab()
    
    with tabs[3]:
        render_test_agent_tab()


def render_create_agent_tab():
    """Render create new agent tab."""
    st.subheader("Create New Custom Agent")
    
    col1, col2 = st.columns(2)
    
    with col1:
        agent_name = st.text_input(
            "Agent Name",
            placeholder="e.g., 'Risk Taker' or 'The Professor'"
        )
        agent_type = st.selectbox(
            "Agent Type",
            ["sharp", "insider", "degen", "bookie"],
            help="Sharp: data-driven | Insider: information-based | Degen: high-risk | Bookie: market-aware"
        )
        risk_tolerance = st.slider(
            "Risk Tolerance",
            0.0, 1.0, 0.5,
            step=0.1,
            help="0.0 = conservative, 1.0 = aggressive"
        )
    
    with col2:
        confidence_threshold = st.slider(
            "Confidence Threshold",
            0.0, 1.0, 0.6,
            step=0.05,
            help="Minimum confidence needed to place bet"
        )
        max_bet_size = st.number_input(
            "Max Bet Size (€)",
            value=100.0,
            min_value=10.0,
            max_value=1000.0,
            step=10.0
        )
    
    st.markdown("---")
    
    st.subheader("Personality & Strategy")
    
    personality = st.text_area(
        "Custom Personality Prompt",
        placeholder="""Example: You are a quantitative analyst who relies on statistical models and historical data. 
You favor teams with strong defensive records and avoid bets with implied odds too close to 50%. 
Your confidence increases when you find edges of 3%+ in expected value.""",
        height=150
    )
    
    description = st.text_area(
        "Agent Description",
        placeholder="What makes this agent unique? What's their betting philosophy?",
        height=100
    )
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info("💡 **Tip**: Be specific about decision-making criteria and avoid overly generic descriptions.")
    
    with col2:
        if st.button("Preview Agent", key="preview_create"):
            render_agent_preview({
                "name": agent_name,
                "type": agent_type,
                "personality": personality,
                "risk_tolerance": risk_tolerance,
                "confidence_threshold": confidence_threshold,
                "max_bet_size": max_bet_size
            })
    
    with col3:
        if st.button("✅ Create Agent", key="create_agent"):
            if not agent_name:
                st.error("Agent name is required")
            elif not personality:
                st.error("Personality/strategy is required")
            else:
                builder = CustomAgentBuilder()
                config = CustomAgentConfig(
                    name=agent_name,
                    agent_type=agent_type,
                    personality=personality,
                    risk_tolerance=risk_tolerance,
                    confidence_threshold=confidence_threshold,
                    max_bet_size=max_bet_size,
                    description=description
                )
                
                created = builder.create_agent(
                    st.session_state.user_id,
                    config
                )
                
                if created:
                    st.success(f"✅ Created agent '{agent_name}'!")
                    st.rerun()


def render_manage_agents_tab():
    """Render manage existing agents tab."""
    st.subheader("Manage Your Agents")
    
    builder = CustomAgentBuilder()
    agents = builder.get_agents(st.session_state.user_id)
    
    if not agents:
        st.info("You haven't created any custom agents yet. Create one in the 'Create New' tab!")
        return
    
    for agent in agents:
        with st.expander(f"🎭 {agent.name} ({agent.agent_type.title()})", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Description**: {agent.description or 'N/A'}")
                st.write(f"**Risk Tolerance**: {agent.risk_tolerance:.1%}")
                st.write(f"**Confidence Threshold**: {agent.confidence_threshold:.1%}")
                st.write(f"**Max Bet Size**: €{agent.max_bet_size:.2f}")
                st.write(f"**Created**: {agent.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                with st.expander("View Personality Prompt"):
                    st.code(agent.personality_prompt)
            
            with col2:
                if st.button("✏️ Edit", key=f"edit_{agent.id}"):
                    st.session_state.editing_agent_id = agent.id
                    st.rerun()
                
                if st.button("🗑️ Delete", key=f"delete_{agent.id}"):
                    if builder.delete_agent(agent.id):
                        st.success(f"Deleted {agent.name}")
                        st.rerun()
    
    # Handle editing if agent selected
    if st.session_state.get("editing_agent_id"):
        agent_id = st.session_state.editing_agent_id
        agent = builder.get_agent(agent_id)
        
        if agent:
            st.markdown("---")
            st.subheader(f"Editing: {agent.name}")
            
            new_name = st.text_input("Agent Name", value=agent.name)
            new_type = st.selectbox("Agent Type", ["sharp", "insider", "degen", "bookie"], index=["sharp", "insider", "degen", "bookie"].index(agent.agent_type))
            new_personality = st.text_area("Personality Prompt", value=agent.personality_prompt, height=150)
            new_risk = st.slider("Risk Tolerance", 0.0, 1.0, agent.risk_tolerance, step=0.1)
            new_confidence = st.slider("Confidence Threshold", 0.0, 1.0, agent.confidence_threshold, step=0.05)
            new_max_bet = st.number_input("Max Bet Size", value=agent.max_bet_size, min_value=10.0)
            new_description = st.text_area("Description", value=agent.description or "", height=100)
            
            if st.button("💾 Save Changes"):
                config = CustomAgentConfig(
                    name=new_name,
                    agent_type=new_type,
                    personality=new_personality,
                    risk_tolerance=new_risk,
                    confidence_threshold=new_confidence,
                    max_bet_size=new_max_bet,
                    description=new_description
                )
                
                if builder.update_agent(agent_id, config):
                    st.success("Agent updated!")
                    del st.session_state.editing_agent_id
                    st.rerun()


def render_agent_gallery_tab():
    """Render agent templates gallery."""
    st.subheader("Agent Gallery & Templates")
    
    st.info("Popular agent archetypes to use as inspiration for your custom agents.")
    
    templates = [
        {
            "name": "The Mathematician",
            "type": "sharp",
            "description": "Relies purely on statistical models and expected value.",
            "personality": "You are a quantitative analyst. Every decision must be backed by statistical evidence. You calculate expected value for every bet and only place wagers with EV > 3%. You avoid hunches and emotion-based reasoning entirely."
        },
        {
            "name": "The Insider",
            "type": "insider",
            "description": "Values information advantage and hidden signals.",
            "personality": "You have access to exclusive information networks. You identify bets where public information differs from true probability. You're willing to take contrarian positions when your intel suggests good value."
        },
        {
            "name": "The Chaos Agent",
            "type": "degen",
            "description": "High-risk, high-reward betting with intuitive calls.",
            "personality": "You trust your gut and aren't afraid of big bets. You look for chaotic, undervalued situations and exploit them aggressively. You believe fortune favors the bold."
        },
        {
            "name": "The Market Maker",
            "type": "bookie",
            "description": "Exploits market psychology and public biases.",
            "personality": "You understand market psychology deeply. You exploit the fact that public money is inefficient. You fade the public when appropriate and follow sharp money movements."
        }
    ]
    
    cols = st.columns(2)
    
    for idx, template in enumerate(templates):
        with cols[idx % 2]:
            with st.container(border=True):
                st.subheader(f"📋 {template['name']}")
                st.caption(f"Type: {template['type'].title()}")
                st.write(template['description'])
                
                if st.button(f"Use as Template", key=f"template_{idx}"):
                    # Pre-fill form with template
                    st.session_state.template_selected = template
                    st.rerun()


def render_test_agent_tab():
    """Render agent testing interface."""
    st.subheader("Test Custom Agent")
    
    builder = CustomAgentBuilder()
    agents = builder.get_agents(st.session_state.user_id)
    
    if not agents:
        st.info("Create a custom agent first to test it.")
        return
    
    selected_agent = st.selectbox(
        "Select Agent to Test",
        agents,
        format_func=lambda a: f"{a.name} ({a.agent_type})"
    )
    
    st.markdown("---")
    st.write(f"**Testing**: {selected_agent.name}")
    st.write(f"**Type**: {selected_agent.agent_type.title()}")
    st.write(f"**Risk Tolerance**: {selected_agent.risk_tolerance:.1%}")
    st.write(f"**Confidence Threshold**: {selected_agent.confidence_threshold:.1%}")
    
    # Test game setup
    st.subheader("Test Game")
    
    col1, col2 = st.columns(2)
    
    with col1:
        team1 = st.text_input("Team 1")
        odds1 = st.number_input("Team 1 Odds (decimal)", value=2.0, step=0.1)
    
    with col2:
        team2 = st.text_input("Team 2")
        odds2 = st.number_input("Team 2 Odds (decimal)", value=2.0, step=0.1)
    
    if st.button("🔍 Test Agent"):
        st.info("Agent testing framework ready for integration with live agent execution.")
        st.write(f"Would test {selected_agent.name} against {team1} vs {team2}")


def render_agent_preview(agent_config: Dict[str, Any]):
    """Render a preview of agent characteristics."""
    st.subheader("Agent Preview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Type", agent_config.get("type", "N/A").title())
    
    with col2:
        st.metric("Risk Tolerance", f"{agent_config.get('risk_tolerance', 0):.0%}")
    
    with col3:
        st.metric("Confidence Threshold", f"{agent_config.get('confidence_threshold', 0):.0%}")
    
    with col4:
        st.metric("Max Bet", f"€{agent_config.get('max_bet_size', 0):.2f}")
    
    st.write("**Personality**:")
    st.code(agent_config.get("personality", ""), language="markdown")
