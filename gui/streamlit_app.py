"""Streamlit GUI for Bratislava Betting Syndicate."""

import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.odds_api import OddsAPIClient
from simulation.graph import SyndicateGraph, run_simulation
from simulation.bankroll import BankrollManager
from gui.visualizations import (
    create_roi_chart,
    create_bankroll_chart,
    create_agent_comparison,
    create_win_rate_chart,
    create_bet_distribution
)
from config.settings import settings


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


def main():
    """Main Streamlit app."""
    init_session_state()

    # Header
    st.markdown('<h1 class="main-header">🎰 Bratislava Betting Syndicate 🎰</h1>', unsafe_allow_html=True)
    st.markdown("### Multi-Agent AI Betting Simulation powered by LangGraph + Claude")

    # Sidebar
    with st.sidebar:
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
    if run_button:
        with st.spinner("🎲 Running simulation..."):
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

            # Run simulation
            results = run_simulation(
                games=games,
                num_games=num_games,
                starting_bankroll=starting_bankroll
            )

            st.session_state.results = results
            st.session_state.simulation_run = True

            st.success("✅ Simulation complete!")

    # Display results
    if st.session_state.simulation_run and st.session_state.results:
        results = st.session_state.results
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
            if st.button("💾 Download CSV"):
                import pandas as pd
                df = pd.DataFrame(bet_results)
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download Bet History CSV",
                    csv,
                    "betting_history.csv",
                    "text/csv"
                )

    else:
        # Welcome screen
        st.info("👈 Configure settings in the sidebar and click 'Run Simulation' to start!")

        st.header("🎯 How It Works")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("1. Data Ingestion")
            st.write("Pull real-time odds from TheOddsAPI or use sample data")

            st.subheader("2. Agent Analysis")
            st.write("10 AI agents analyze each game with different strategies")

            st.subheader("3. Debate Phase")
            st.write("Agents debate their positions and argue for their bets")

        with col2:
            st.subheader("4. Consensus Building")
            st.write("Agents vote on which bet to place")

            st.subheader("5. Kelly Criterion")
            st.write("Optimal bet sizing using Kelly criterion")

            st.subheader("6. Simulation")
            st.write("Run 100+ games and track ROI over time")

        st.header("🤖 Meet the Agents")

        agents_data = {
            "Agent": ["Viktor", "Elena", "Boris", "Nikolai", "Petra", "Jozef", "Marian", "Lucia", "Tomáš", "Katarína"],
            "Type": ["Sharp", "Sharp", "Sharp", "Insider", "Insider", "Degen", "Degen", "Degen", "Bookie", "Bookie"],
            "Philosophy": [
                "Expected value or bust",
                "Closing line value only",
                "Arbitrage specialist",
                "I know a guy at Niké...",
                "The fix is in",
                "YOLO parlay time!",
                "Horoscope-based betting",
                "Always bet home teams",
                "Shade lines, trap squares",
                "Balance books, max juice"
            ]
        }

        import pandas as pd
        st.table(pd.DataFrame(agents_data))


if __name__ == "__main__":
    # Import pandas here to avoid issues
    import pandas as pd
    main()
