# 🎰 Bratislava Betting Syndicate

**Multi-Agent AI Betting Simulation powered by LangGraph + Claude**

Watch 10 AI agents debate, argue, and bet their way through 100 games using real odds data. Sharps analyze Pinnacle lines, insiders leak Niké intel, degens follow gut feelings, and bookies manipulate the market.

## 🔥 Features

- **10 Distinct AI Agents:**
  - 3 Sharps (analytical, Pinnacle odds-based)
  - 2 Insiders (Niké leaks, insider info)
  - 3 Degens (gut feelings, chaos mode)
  - 2 Bookies (line manipulation, market making)

- **Real Data Integration:**
  - TheOddsAPI for live odds
  - Custom scrapers for Niké and regional books
  - Historical data analysis

- **Interactive GUI:**
  - Streamlit dashboard for agent debates
  - Real-time bankroll tracking
  - Vote on parlay suggestions
  - Kelly criterion simulations over 100 games

- **Export & Analytics:**
  - PDF ROI reports with graphs
  - Agent performance metrics
  - Bankroll progression charts

- **Pro Features (€9/month):**
  - Custom agent creation
  - Advanced Kelly strategies
  - Historical backtesting
  - API access

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY and ODDS_API_KEY

# Run the simulation
python main.py

# Or launch Streamlit GUI
streamlit run gui/streamlit_app.py
```

## 🎮 How It Works

1. **Data Ingestion:** Pull real-time odds from TheOddsAPI
2. **Agent Deliberation:** 10 agents analyze games using LangGraph workflows
3. **Debate Phase:** Agents argue their positions (sharps vs degens)
4. **Consensus Building:** Vote on which bets to place
5. **Bankroll Management:** Kelly criterion for optimal bet sizing
6. **Simulation:** Run 100+ games, track ROI
7. **Export:** Generate PDF reports with insights

## 📊 Agent Personalities

- **Viktor (Sharp):** "Expected value or bust"
- **Elena (Sharp):** "Pinnacle closing line value only"
- **Boris (Sharp):** "Market inefficiencies arbitrage"
- **Nikolai (Insider):** "I know a guy at Niké..."
- **Petra (Insider):** "The fix is in, trust me"
- **Jozef (Degen):** "YOLO parlay time!"
- **Marian (Degen):** "My horoscope says OVER"
- **Lucia (Degen):** "Always bet on red... I mean home teams"
- **Tomáš (Bookie):** "Time to shade this line..."
- **Katarína (Bookie):** "Let's trap the squares"

## 💰 Monetization

Free tier: 10 pre-built agents, 100 game sims
Pro tier (€9/mo): Custom agents, unlimited sims, API access

## 🛠️ Tech Stack

- **LangGraph:** Multi-agent orchestration
- **Claude Sonnet 4.5:** Agent reasoning engine
- **Streamlit:** Interactive GUI
- **Plotly/Matplotlib:** Visualizations
- **ReportLab:** PDF generation
- **TheOddsAPI:** Real-time odds data

## 📈 Example Output

```
=== BRATISLAVA BETTING SYNDICATE - SIMULATION RESULTS ===

Starting Bankroll: €10,000
Final Bankroll: €13,247
Total ROI: +32.47%
Games Simulated: 100
Win Rate: 54.2%

Top Performing Agent: Viktor (Sharp) - +€2,100
Worst Performing Agent: Jozef (Degen) - -€850

Kelly Criterion Performance: Beat flat betting by 18.3%
```

## 🎯 Roadmap

- [ ] Live betting mode (real money tracking)
- [ ] Machine learning agent trainer
- [ ] Multi-sport support (football, basketball, tennis)
- [ ] Discord bot integration
- [ ] Mobile app

## ⚠️ Disclaimer

This is a simulation tool for educational and entertainment purposes. Always gamble responsibly. Past performance doesn't guarantee future results. The house always wins... unless you're Viktor.

## 📝 License

MIT - Build your own syndicate!

---

**Made with chaos in Bratislava 🇸🇰**
