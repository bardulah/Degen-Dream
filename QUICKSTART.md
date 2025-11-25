# Quick Start Guide - Bratislava Betting Syndicate

## 🎯 What is This?

Multi-agent AI betting simulation system where 10 different AI agents (with different personalities and strategies) analyze sports odds and place collaborative bets. The system includes:

- **CLI Simulation Engine**: Real-time agent analysis and betting
- **FastAPI REST API**: Full CRUD operations for simulations and user management
- **Web Dashboard**: HTML5 interface to view results and user stats
- **Database Persistence**: SQLite (dev) or PostgreSQL (prod)
- **PDF Reports**: Export simulation results as professional reports

---

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

For development, key packages are:
```bash
pip install langgraph langchain anthropic fastapi uvicorn sqlalchemy google-generativeai openai
```

### 2. Set Environment Variables
```bash
cp .env.example .env
# Edit .env with your API keys:
# - ANTHROPIC_API_KEY
# - GOOGLE_API_KEY
# - STRIPE_SECRET_KEY (optional)
```

### 3. Initialize Database
```bash
python -c "from database.schema import init_db; init_db(); print('✅ Database initialized')"
```

### 4. Run Your First Simulation
```bash
python main.py --games 5 --sport soccer_epl
```

This will:
- Fetch 20 live EPL matches
- Run agents to analyze the first 5 games
- Place bets based on agent consensus
- Save results to database

**Output**: Agent analysis → Debate → Bet placement → ROI/Win rate stats

---

## 🚀 Running the API Server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Navigate to:
- **Swagger Docs**: http://localhost:8000/docs
- **Dashboard UI**: http://localhost:8000/static/dashboard.html
- **Health Check**: http://localhost:8000/api/health

### Register a New User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secure123"}'

# Returns JWT token + user_id
```

### View Dashboard
```bash
# Use your user_id from registration above
curl http://localhost:8000/api/dashboard \
  -H "user-id: YOUR_USER_ID"
```

---

## 📊 Available CLI Commands

### Run Simulation
```bash
python main.py \
  --games 10           # Number of games to analyze
  --sport soccer_epl   # Sport (soccer_epl, nba, mlb, nfl)
  --sample             # Use sample data instead of live API
  --no-live            # Disable real-time visualization
```

### View Simulations
```bash
python -c "
from database.schema import SessionLocal, Simulation
db = SessionLocal()
sims = db.query(Simulation).order_by(Simulation.created_at.desc()).limit(5)
for sim in sims:
    print(f'{sim.sport}: ROI={sim.roi}%, WR={sim.win_rate}%')
db.close()
"
```

### Generate PDF Report
```python
from export import PDFGenerator
from database.schema import SessionLocal, Simulation

db = SessionLocal()
sim = db.query(Simulation).order_by(Simulation.created_at.desc()).first()

gen = PDFGenerator()
gen.generate_report(
    sim.id,
    'user@example.com',
    {
        'stats': {
            'starting_bankroll': sim.starting_bankroll,
            'current_bankroll': sim.final_bankroll,
            'roi': sim.roi,
            'win_rate': sim.win_rate,
            'total_bets': sim.total_bets,
            'total_wagered': sim.total_wagered,
            'max_drawdown': sim.max_drawdown or 0,
            'duration_seconds': sim.duration_seconds or 0
        }
    },
    []  # agent_stats
)
db.close()
```

---

## 🤖 The 10 AI Agents

### Sharp Traders (3 agents)
- **Viktor**: Data-driven, models odds efficiency
- **Elena**: Quant-focused, statistical analysis
- **Boris**: Value hunter, EV calculator

### Insider Traders (2 agents)
- **Nikolai**: Generates fake "training ground" rumors
- **Petra**: Creates false "insider" injury news

### Degen Gamblers (3 agents)
- **Jozef**: Moon phases, numerology, vibes
- **Marian**: Random high-confidence bets
- **Lucia**: Emotional betting, "feels"

### Bookie/Sharp (2 agents)
- **Tomáš**: Line manipulation strategy
- **Katarína**: Public money tracking

Each agent has a unique personality and decision-making style. They debate openly and vote on consensus bets.

---

## 📁 Project Structure

```
Degen-Dream/
├── main.py                      # CLI entry point
├── api/
│   ├── main.py                 # FastAPI app
│   ├── routes/
│   │   ├── auth.py            # Login/register
│   │   ├── simulations.py      # Sim CRUD
│   │   ├── agents.py           # Custom agents
│   │   └── subscriptions.py    # Stripe webhooks
│   └── static/
│       └── dashboard.html      # Web UI
├── database/
│   ├── schema.py               # SQLAlchemy models
│   ├── auth.py                 # JWT + rate limiting
│   └── simulation_store.py     # Persistence
├── simulation/
│   ├── graph.py                # Agent orchestration
│   ├── bankroll.py             # Bankroll tracking
│   ├── bet_probability.py      # Realistic odds
│   └── agent_learning.py       # Confidence weighting
├── agents/
│   ├── base_agent.py           # Agent interface
│   ├── sharp_agent.py          # Sharp traders
│   ├── insider_agent.py        # Insider info
│   ├── degen_agent.py          # Gamblers
│   └── bookie_agent.py         # Bookies
├── data/
│   └── odds_aggregator.py      # Fetch live odds
├── export/
│   └── pdf_generator.py        # PDF reports
└── monitoring/
    └── logger.py               # Structured logging
```

---

## 🔐 Tier System

### FREE (Default)
- 3 simulations/day
- 100 games max per simulation
- No custom agents
- No API access

### PRO ($9.99/month)
- 50 simulations/day
- 1000 games per simulation
- 50 custom agents
- API access
- PDF export

### ENTERPRISE (Custom)
- Unlimited simulations
- Unlimited games
- Unlimited agents
- White-label options
- Dedicated support

---

## 🧪 Testing

### Test Core Simulation
```bash
timeout 60 python main.py --games 3 --sport soccer_epl
```

### Test API
```bash
# Terminal 1: Start server
uvicorn api.main:app --reload

# Terminal 2: Run tests
python -c "
import requests
resp = requests.post('http://localhost:8000/api/auth/register',
    json={'email': 'test@example.com', 'password': 'test123'})
print(resp.json())
"
```

### Test Database
```bash
python -c "
from database.schema import init_db, SessionLocal, User, Simulation
init_db()
db = SessionLocal()
print(f'Users: {db.query(User).count()}')
print(f'Simulations: {db.query(Simulation).count()}')
db.close()
"
```

---

## 🐛 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'langchain'`
**Solution**: `pip install langchain langgraph anthropic google-generativeai openai`

### Issue: `sqlite3.OperationalError: database is locked`
**Solution**: Close other processes using `bratislava.db`, or delete it to reinitialize

### Issue: Streamlit won't install (pyarrow error)
**Solution**: Use the CLI or web API instead. Streamlit dependency is optional.

### Issue: API endpoints return 401
**Solution**: Include the `user-id` header in all requests, or register a new user first

### Issue: Simulations show `in_progress` status
**Solution**: Run simulation to completion. Incomplete sims stay `in_progress` in DB. Check logs for errors.

---

## 📚 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Health check |
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| GET | `/api/user/profile` | User details + stats |
| POST | `/api/user/generate-api-key` | Get API key |
| GET | `/api/dashboard` | Dashboard data |
| GET | `/api/stats/overview` | Aggregate stats |
| POST | `/api/simulations` | Start simulation |
| GET | `/api/simulations` | List simulations |
| GET | `/api/simulations/{id}` | Get details |
| GET | `/api/simulations/{id}/export-pdf` | Download PDF |

Full docs at: http://localhost:8000/docs

---

## 🎯 Next Steps

1. **Run a simulation**: `python main.py --games 10`
2. **Start the API**: `uvicorn api.main:app --reload`
3. **Open dashboard**: http://localhost:8000/static/dashboard.html
4. **Check logs**: `tail -f logs/app.log`
5. **Review results**: Query database or use API

---

## 📞 Support

- **Docs**: See `README.md`, `AGENTS.md`, `STATUS.md`
- **Issues**: Check `logs/` folder
- **Database**: Use `sqlite3 bratislava.db` or DBeaver
- **API Errors**: Check console output or `/api/health`

---

**Version**: 1.0.0 (MVP)  
**Status**: ✅ Production Ready for Testing  
**Last Updated**: November 25, 2025
