# Bratislava Betting Syndicate - Documentation Index

**Project Status**: MVP Ready ✅ | Session 7 Complete | Oracle Agent + Email UX Shipped

---

## 📖 Documentation Files

### For Quick Start
- **[QUICK START](QUICK_START.md)** - 5 minute setup guide
- **[AGENTS.md](AGENTS.md)** - **START HERE** - Complete project documentation
- **[HANDOFF.md](HANDOFF.md)** - Session 7 summary for next developer

### Session Documentation
- **[SESSION_7_SUMMARY.md](SESSION_7_SUMMARY.md)** - What changed this session
- **[SESSION_6_SUMMARY.md](SESSION_6_SUMMARY.md)** - Previous session (Discord)
- **[DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md)** - Overall project history

### Technical Docs
- **[DAILY_SETUP.md](DAILY_SETUP.md)** - Daily deployment instructions
- **[EMAIL_SETUP.md](EMAIL_SETUP.md)** - Email configuration
- **[DISCORD_QUICKSTART.md](DISCORD_QUICKSTART.md)** - Discord webhook setup

### Reference
- **[README.md](README.md)** - Project overview
- **[STATUS.md](STATUS.md)** - Current implementation status

---

## 🎯 What This Project Does

**Multi-Agent AI Betting Syndicate**: 10 agents with different personalities (sharps, insiders, degens, bookies) analyze sports matches, debate picks, and decide on bets together.

### Core Features
1. ✅ Daily odds fetching from Nike.sk + OddsAPI
2. ✅ Multi-agent analysis (10 agents with unique personalities)
3. ✅ Debate phase (agents discuss their positions)
4. ✅ **Oracle agent** (synthesizes all opinions + LLM decision)
5. ✅ **Democratic voting** (shown for comparison)
6. ✅ Email reports with clean layout
7. ✅ Discord notifications
8. ✅ Real-time context (Gemini Search for injuries/news)
9. ✅ Database persistence (SQLite/PostgreSQL)
10. ⏳ Results fetching (real scores) - **NEXT FEATURE**

---

## 🚀 Getting Started (3 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Keys
```bash
export OPENROUTER_API_KEY="your-openrouter-key"
export SENDER_EMAIL="your@gmail.com"
export SENDER_PASSWORD="app-password"
export CLI_USER_EMAIL="your@gmail.com"
```

### 3. Run
```bash
python main.py --daily --games 3 --no-live
```

**See [AGENTS.md](AGENTS.md) for full setup instructions.**

---

## 📊 Current Status

### What Works ✅
- Daily odds fetching (Nike.sk + OddsAPI)
- 10 agent personalities (each unique)
- Debate system (first 5 agents discuss)
- Oracle agent (LLM analyzes all picks)
- Democratic voting (transparent vote counts)
- Email reports (HTML with draw odds support)
- Discord notifications
- Database persistence
- Gemini Search grounding (real-time news/injuries)

### What's Missing ⏳
- Results fetching (real match scores)
- Bet settlement (WON/LOST tracking)
- Agent learning (confidence calibration)
- Dashboard (Streamlit visualization)
- Docker setup
- Unit tests

---

## 🔍 Quick Reference

### Most Important Files
| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `agents/oracle_agent.py` | Oracle agent (new) |
| `simulation/graph.py` | Agent orchestration |
| `agents/{sharp,insider,degen,bookie}_agent.py` | Agent personalities |
| `notification/email_sender.py` | Email formatting |
| `data/daily_odds_fetcher.py` | Odds fetching |

### Key Concepts

**Voting vs Oracle**
- **Vote**: Simple majority (each agent = 1 vote)
- **Oracle**: LLM analyzes all picks + reasoning, makes informed decision
- Both run in parallel, shown for comparison

**Agent Types**
- **Sharps** (3): Data-driven, EV focused
- **Insiders** (2): Leaked info, injury angles  
- **Degens** (3): Chaos, superstitions, fun
- **Bookies** (2): Market trapping, line movement

**Key Features**
- Gemini Search integration (real-time context)
- 3-way odds support (home/draw/away)
- Email reports with betting logic
- Discord webhook notifications
- SQLite/PostgreSQL persistence

---

## 🎓 Learning Paths

### New to the Project?
1. Read [QUICK_START.md](QUICK_START.md)
2. Run `python main.py --games 3 --sample --no-live`
3. Check the email report
4. Read [AGENTS.md](AGENTS.md) architecture section

### Want to Add Features?
1. Review [SESSION_7_SUMMARY.md](SESSION_7_SUMMARY.md) (latest changes)
2. Check [HANDOFF.md](HANDOFF.md) for recommendations
3. Look at relevant agent code in `agents/`
4. See AGENTS.md next steps section

### Want to Debug?
1. Check [AGENTS.md](AGENTS.md) troubleshooting section
2. Enable debug mode: `export LOG_LEVEL="DEBUG"`
3. Run with `--no-live` to avoid Discord
4. Use `--sample` to test without APIs

---

## 📋 Session 7 Changes

### What I Added
- **Oracle Agent** (`agents/oracle_agent.py`) - LLM analyzes all picks
- **Draw Odds** - 3-way markets (home/draw/away)
- **Email Layout** - Better sections and readability
- **Voting vs Oracle** - Both mechanisms shown in parallel

### Files Modified
- `agents/base_agent.py` - Added draw_odds field
- `data/odds_api.py` - Added draw odds parsing
- `simulation/graph.py` - Oracle integration + voting
- `notification/email_sender.py` - Layout improvements
- `AGENTS.md` - Updated documentation

### Testing
- ✅ 3 real matches (Arsenal, Slovan, Copenhagen)
- ✅ Email generation with full layout
- ✅ Oracle agent LLM calls
- ✅ Database persistence

---

## 🔗 How the System Works

```
CLI (main.py)
  ↓
Fetch Odds (Nike.sk + OddsAPI)
  ↓
Analyze Game (10 agents)
  ├─ Real-time context (Gemini Search)
  ├─ LLM calls (Gemini 2.0 Flash via OpenRouter)
  ├─ Each agent returns bet proposal
  ↓
Debate Phase (first 5 agents discuss)
  ↓
Decision Making
  ├─ Democratic vote (count votes per team)
  └─ Oracle analysis (LLM synthesizes all picks)
  ↓
Place Bet (best option from decision)
  ↓
Save to Database (PENDING status)
  ↓
Notify
  ├─ Email report (HTML)
  └─ Discord message
```

---

## 💡 Tips

### For Running Locally
- Use `--sample` flag to avoid API costs during testing
- Use `--no-live` to skip Discord (faster)
- Check console output for detailed agent reasoning

### For Extending
- Agents inherit from `BaseAgent` - easy to add new types
- LLM provider configurable in `config/settings.py`
- Database models in `database/schema.py`

### For Troubleshooting
- Check `AGENTS.md` troubleshooting section first
- Enable debug logging: `export LOG_LEVEL="DEBUG"`
- Run with `--sample --no-live` for offline testing

---

## 🎯 Recommended Next Steps

1. **Results Matching** (2-3 hours) - Most important for metrics
2. **Discord Enhancements** (1-2 hours) - Most fun and engaging
3. **Agent Learning** (1-2 hours) - Most valuable for improvement

See [HANDOFF.md](HANDOFF.md) for detailed recommendations.

---

## 📞 Need Help?

1. **Setup Issues** → [AGENTS.md](AGENTS.md) "HOW TO RUN" section
2. **Troubleshooting** → [AGENTS.md](AGENTS.md) "TROUBLESHOOTING" section
3. **Architecture** → [AGENTS.md](AGENTS.md) "ARCHITECTURE OVERVIEW" section
4. **Changes This Session** → [SESSION_7_SUMMARY.md](SESSION_7_SUMMARY.md)
5. **Handoff Info** → [HANDOFF.md](HANDOFF.md)

---

**Last Updated**: Nov 26, 2025 (Session 7)  
**Status**: MVP Ready ✅  
**Next**: Results Fetching or Discord Enhancements  
