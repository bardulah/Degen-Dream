"""Streamlit GUI for Bratislava Betting Syndicate."""

import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.odds_api import OddsAPIClient
from simulation.graph import run_simulation
from simulation.bankroll import BankrollManager
from gui.visualizations import (
    create_roi_chart,
    create_bankroll_chart,
    create_agent_comparison,
    create_win_rate_chart,
    create_bet_distribution
)
from config.settings import settings
from database.schema import init_db, SessionLocal, User, Simulation, Bet
from database.auth import auth_manager, UserTier
from database.simulation_store import SimulationStore
import uuid
from datetime import datetime
import pandas as pd


# Page config
st.set_page_config(
    page_title="Bratislava Betting Syndicate",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #2ecc71, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stButton>button {
        width: 100%;
        background-color: #2ecc71;
        color: white;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'simulation_run' not in st.session_state:
        st.session_state.simulation_run = False
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'syndicate' not in st.session_state:
        st.session_state.syndicate = None


def login_page():
    """Render login page."""
    st.markdown('<h1 class="main-header">🎰 Bratislava Betting Syndicate 🎰</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("🔑 Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            db = SessionLocal()
            user = auth_manager.authenticate_user(db, email, password)
            if user:
                # Store minimal user info in session state
                st.session_state.user_id = user.id
                st.session_state.user_email = user.email
                st.session_state.user_tier = user.tier
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid email or password")
            db.close()
        
        st.markdown("---")
        if st.button("Create Account (Free Tier)"):
            st.session_state.page = "register"
            st.rerun()


def register_page():
    """Render registration page."""
    st.markdown('<h1 class="main-header">🎰 Bratislava Betting Syndicate 🎰</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("📝 Register")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        
        if st.button("Register"):
            if password != confirm:
                st.error("Passwords do not match")
                return
                
            db = SessionLocal()
            try:
                user = auth_manager.create_user(db, email, password)
                st.success("Account created! Please login.")
                st.session_state.page = "login"
                st.rerun()
            except Exception as e:
                st.error(f"Error creating account: {str(e)}")
            finally:
                db.close()
                
        if st.button("Back to Login"):
            st.session_state.page = "login"
            st.rerun()


def simulation_interface():
    """Render main simulation interface."""
    # Sidebar
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_email}**")
        st.caption(f"Tier: {st.session_state.user_tier.value.upper()}")
        
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.rerun()
            
        st.markdown("---")
        st.header("⚙️ Simulation Settings")

        num_games = st.slider("Number of Games", 10, 200, 100)
        starting_bankroll = st.number_input("Starting Bankroll (€)", 1000, 100000, 10000, 1000)
        kelly_fraction = st.slider("Kelly Fraction", 0.1, 0.5, 0.25, 0.05)

        st.markdown("---")
        st.header("🔧 Data Source")
        use_live_data = st.checkbox("Use Live API Data", False)

        if use_live_data:
            sport = st.selectbox(
                "Sport",
                ["soccer_epl", "basketball_nba", "americanfootball_nfl", "icehockey_nhl"]
            )
        else:
            sport = "sample"
            st.info("Using sample data (no API calls)")

        st.markdown("---")
        run_button = st.button("🚀 Run Simulation", type="primary")

        st.markdown("---")
        st.header("📊 Agent Types")
        st.write("**3 Sharps** 🧠")
        st.caption("Viktor, Elena, Boris")
        st.write("**2 Insiders** 🤫")
        st.caption("Nikolai, Petra")
        st.write("**3 Degens** 🎲")
        st.caption("Jozef, Marian, Lucia")
        st.write("**2 Bookies** 📊")
        st.caption("Tomáš, Katarína")

    # Main content
    st.markdown('<h1 class="main-header">🎰 Bratislava Betting Syndicate 🎰</h1>', unsafe_allow_html=True)
    
    # Tabs for Run vs History vs Custom Agents
    tab_run, tab_history, tab_agents = st.tabs(["🚀 Run Simulation", "📜 History", "🎭 Custom Agents"])
    
    with tab_run:
        if run_button:
            run_simulation_gui(num_games, starting_bankroll, kelly_fraction, use_live_data, sport)
        
        # Display results if just run
        if st.session_state.simulation_run and st.session_state.results:
            display_results(st.session_state.results)
            
    with tab_history:
        display_history()
    
    with tab_agents:
        # Tier check for custom agent feature
        if st.session_state.user_tier == "free":
            st.warning("⚠️ Custom agents are a Pro feature. Upgrade your tier to create custom agents.")
        else:
            from gui.agent_builder import render_agent_builder_ui
            render_agent_builder_ui()


def run_simulation_gui(num_games, starting_bankroll, kelly_fraction, use_live_data, sport):
    """Run simulation from GUI with live updates."""
    from gui.live_updates import LiveBankrollTicker, SimulationProgressBar
    from simulation.event_emitter import event_emitter, SimulationEventType, reset_emitter
    
    # Update settings
    settings.SIMULATION_GAMES = num_games
    settings.STARTING_BANKROLL = starting_bankroll
    settings.KELLY_FRACTION = kelly_fraction

    # Fetch data
    odds_client = OddsAPIClient()
    if use_live_data:
        games = odds_client.get_odds(sport=sport)
        if not games:
            st.warning("No live games found, using sample data")
            games = odds_client.get_sample_games()
    else:
        games = odds_client.get_sample_games()

    # Prepare DB
    db = SessionLocal()
    user_id = st.session_state.user_id
    
    # Create simulation record
    simulation_id = str(uuid.uuid4())
    simulation = Simulation(
        id=simulation_id,
        user_id=user_id,
        num_games=num_games,
        starting_bankroll=starting_bankroll,
        kelly_fraction=kelly_fraction,
        sport=sport,
        use_live_data=use_live_data,
        status="in_progress",
        created_at=datetime.utcnow()
    )
    db.add(simulation)
    db.commit()

    # Reset event emitter for new simulation
    reset_emitter()
    
    # Create live update containers
    progress_container = st.container()
    bankroll_container = st.container()
    game_container = st.container()
    
    with progress_container:
        progress_bar = SimulationProgressBar(num_games)
        progress_placeholder = st.empty()
    
    with bankroll_container:
        ticker = LiveBankrollTicker(starting_bankroll)
        ticker_placeholder = st.empty()
    
    # Setup event listeners
    def on_bet_result(event):
        """Update on bet result."""
        with progress_placeholder.container():
            result = event.data.get('result')
            progress_bar.update(result == 'win')
            progress_bar.display()
        
        with ticker_placeholder.container():
            ticker.update(
                event.data.get('bankroll', starting_bankroll),
                event.game_number,
                event.data.get('roi', 0),
                event.data.get('win_rate', 0)
            )
            ticker.display()
    
    event_emitter.on(SimulationEventType.BET_RESULT, on_bet_result)
    
    # Run simulation
    try:
        results = run_simulation(
            games=games,
            num_games=num_games,
            starting_bankroll=starting_bankroll,
            db=db,
            user_id=user_id,
            simulation_id=simulation_id,
            sport=sport,
            use_live_data=use_live_data
        )

        st.session_state.results = results
        st.session_state.simulation_run = True
        st.success("✅ Simulation complete!")
        
    except Exception as e:
        st.error(f"Simulation failed: {str(e)}")
        # Mark failed in DB
        SimulationStore.mark_simulation_failed(db, simulation_id, str(e))
    finally:
        db.close()


def display_results(results):
    """Display simulation results."""
    stats = results["stats"]
    agent_stats = results["agent_stats"]
    performance = results["performance"]
    bet_results = results["results"]

    # Key metrics
    st.header("📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Final Bankroll",
            f"€{stats['current_bankroll']:.2f}",
            f"{stats['profit_loss']:+.2f} EUR"
        )

    with col2:
        st.metric(
            "ROI",
            f"{stats['roi']:.2f}%",
            "vs starting bankroll"
        )

    with col3:
        st.metric(
            "Win Rate",
            f"{stats['win_rate']:.1f}%",
            f"{stats['wins']} wins / {stats['losses']} losses"
        )

    with col4:
        st.metric(
            "Total Wagered",
            f"€{stats['total_wagered']:.2f}",
            f"Avg: €{stats['average_bet_size']:.2f}"
        )

    # Charts
    st.header("📈 Performance Charts")

    tab1, tab2, tab3 = st.tabs(["Bankroll & ROI", "Agent Performance", "Bet Analysis"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_bankroll_chart(performance), use_container_width=True)
        with col2:
            st.plotly_chart(create_roi_chart(performance), use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_agent_comparison(agent_stats), use_container_width=True)
        with col2:
            st.plotly_chart(create_win_rate_chart(agent_stats), use_container_width=True)

    with tab3:
        col1, col2 = st.columns([2, 1])
        with col1:
            # Bet history table
            st.subheader("Recent Bets")
            df = pd.DataFrame(bet_results[-20:])  # Last 20 bets
            st.dataframe(df, use_container_width=True)
        with col2:
            st.plotly_chart(create_bet_distribution(bet_results), use_container_width=True)

    # Agent leaderboard
    st.header("🏆 Agent Leaderboard")

    sorted_agents = sorted(agent_stats, key=lambda x: x['roi'], reverse=True)

    for i, agent in enumerate(sorted_agents, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        type_emoji = {
            "sharp": "🧠",
            "insider": "🤫",
            "degen": "🎲",
            "bookie": "📊"
        }.get(agent['type'], "")

        with st.expander(f"{emoji} {i}. {agent['name']} {type_emoji} - ROI: {agent['roi']:+.2f}%"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Bankroll", f"€{agent['bankroll']:.2f}")
                st.metric("Total Bets", agent['total_bets'])

            with col2:
                st.metric("Wins", agent['wins'])
                st.metric("Losses", agent['losses'])

            with col3:
                st.metric("Win Rate", f"{agent['win_rate']:.1f}%")
                st.metric("Profit/Loss", f"€{agent['profit_loss']:+.2f}")

    # Download report
    st.header("📥 Export Results")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Generate PDF Report"):
            st.info("PDF export coming soon! Check export/pdf_generator.py")

    with col2:
        import pandas as pd
        df = pd.DataFrame(bet_results)
        csv = df.to_csv(index=False)
        st.download_button(
            "Download Bet History CSV",
            csv,
            "betting_history.csv",
            "text/csv"
        )


def display_history():
    """Display simulation history."""
    st.header("📜 Simulation History")
    
    db = SessionLocal()
    try:
        sims = SimulationStore.get_user_simulations(db, st.session_state.user_id, limit=20)
        
        if not sims:
            st.info("No simulation history found.")
            return
            
        history_data = []
        for sim in sims:
            history_data.append({
                "Date": sim.created_at.strftime("%Y-%m-%d %H:%M"),
                "ROI": f"{sim.roi:.2f}%" if sim.roi else "0.00%",
                "Bankroll": f"€{sim.final_bankroll:.2f}" if sim.final_bankroll else "-",
                "Win Rate": f"{sim.win_rate:.1f}%" if sim.win_rate else "-",
                "Bets": sim.total_bets,
                "Status": sim.status
            })
            
        st.dataframe(pd.DataFrame(history_data), use_container_width=True)
        
    finally:
        db.close()


def main():
    """Main Streamlit app."""
    init_db()  # Ensure DB exists
    init_session_state()

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        
    if not st.session_state.authenticated:
        if st.session_state.get('page') == 'register':
            register_page()
        else:
            login_page()
        return
        
    simulation_interface()


if __name__ == "__main__":
    # Import pandas here to avoid issues
    import pandas as pd
    main()
