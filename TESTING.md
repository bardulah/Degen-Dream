# Testing Guide - Bratislava Betting Syndicate

## 🧪 Test Suite Overview

This guide covers manual testing of all core features. For automated tests, see `tests/` directory.

---

## ✅ Pre-Flight Checks

### 1. Dependencies
```bash
python -c "
imports = [
    'langgraph', 'langchain', 'anthropic', 'sqlalchemy',
    'fastapi', 'google.generativeai', 'openai', 'reportlab'
]
for mod in imports:
    __import__(mod)
print('✅ All dependencies available')
"
```

### 2. Database
```bash
python -c "
from database.schema import init_db, SessionLocal, User
init_db()
db = SessionLocal()
users = db.query(User).count()
print(f'✅ Database initialized with {users} users')
db.close()
"
```

### 3. Environment
```bash
python -c "
import os
for key in ['ANTHROPIC_API_KEY', 'GOOGLE_API_KEY']:
    val = os.getenv(key, '').strip()
    if not val:
        print(f'⚠️  {key} not set')
    else:
        print(f'✅ {key} is set ({len(val)} chars)')
"
```

---

## 🎬 Functional Tests

### Test 1: CLI Simulation
**Goal**: Verify end-to-end simulation works

```bash
# Run a 2-game simulation
timeout 90 python main.py --games 2 --sport soccer_epl

# Expected output:
# ✓ Fetches odds from API
# ✓ Shows "Game 1/2", "Game 2/2"
# ✓ Agents analyze each game
# ✓ Shows debate between agents
# ✓ Places consensus bets (✅ BET PLACED)
# ✓ Shows bet outcomes (✓ SUCCESS or ❌ ERROR)
# ✓ Shows final statistics
# ✓ Shows agent performance rankings (🥇 🥈 🥉)
```

**Verify Database**:
```bash
python -c "
from database.schema import SessionLocal, Simulation
db = SessionLocal()
sim = db.query(Simulation).order_by(Simulation.created_at.desc()).first()
assert sim.status == 'completed', f'Status is {sim.status}, should be completed'
assert sim.roi is not None, 'ROI should be set'
assert sim.win_rate is not None, 'Win rate should be set'
print(f'✅ Simulation saved: ROI={sim.roi}%, WR={sim.win_rate}%')
db.close()
"
```

---

### Test 2: API Server
**Goal**: Verify FastAPI endpoints work

```bash
# Terminal 1: Start server
uvicorn api.main:app --host 127.0.0.1 --port 8000 &
sleep 2

# Terminal 2: Run tests
echo "=== Health Check ==="
curl http://localhost:8000/api/health | python -m json.tool

echo -e "\n=== Register User ==="
RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com","password":"test123456"}')
USER_ID=$(echo $RESPONSE | python -c "import sys, json; d=json.load(sys.stdin); print(d['user_id'])")
echo "✅ User ID: $USER_ID"

echo -e "\n=== Get Profile ==="
curl -s -H "user-id: $USER_ID" http://localhost:8000/api/user/profile | python -m json.tool

echo -e "\n=== Get Dashboard ==="
curl -s -H "user-id: $USER_ID" http://localhost:8000/api/dashboard | python -m json.tool | head -30

# Cleanup
pkill -f uvicorn
```

**Expected results**:
- ✅ `/api/health` returns `{"status": "healthy"}`
- ✅ `/api/auth/register` returns user_id + JWT token
- ✅ `/api/user/profile` returns user details + tier
- ✅ `/api/dashboard` returns simulations + stats

---

### Test 3: Database Persistence
**Goal**: Verify all data saves correctly

```python
from database.schema import init_db, SessionLocal, User, Simulation, Bet, AgentSimulationStats
from database.simulation_store import SimulationStore
import uuid

init_db()
db = SessionLocal()

# Get or create test user
user = db.query(User).filter_by(email='test@example.com').first()
if not user:
    from database.auth import AuthManager
    auth = AuthManager()
    user = auth.create_user(db, 'test@example.com', 'test123', 'free')

# Create test simulation
sim_id = str(uuid.uuid4())
result = SimulationStore.save_simulation(
    db=db,
    user_id=user.id,
    simulation_id=sim_id,
    num_games=10,
    starting_bankroll=10000,
    kelly_fraction=0.05,
    sport='test',
    use_live_data=False,
    final_bankroll=10150,
    roi=1.5,
    win_rate=60.0,
    total_bets=10,
    total_wagered=1000,
    max_drawdown=2.0,
    duration_seconds=60,
    agent_stats=[
        {
            'name': 'TestAgent',
            'type': 'sharp',
            'initial_bankroll': 1000,
            'bankroll': 1015,
            'roi': 1.5,
            'total_bets': 10,
            'wins': 6,
            'losses': 4,
            'win_rate': 60.0,
            'profit_loss': 15
        }
    ]
)

assert result, 'Failed to save simulation'

# Verify saved data
sim = db.query(Simulation).filter_by(id=sim_id).first()
assert sim is not None, 'Simulation not found'
assert sim.status == 'completed', f'Status is {sim.status}'
assert sim.roi == 1.5, f'ROI is {sim.roi}'
assert sim.final_bankroll == 10150, f'Final bankroll is {sim.final_bankroll}'

agent_stats = db.query(AgentSimulationStats).filter_by(simulation_id=sim_id).all()
assert len(agent_stats) == 1, f'Found {len(agent_stats)} agent stats'
assert agent_stats[0].agent_name == 'TestAgent', 'Agent name mismatch'

print('✅ All persistence tests passed')
db.close()
```

---

### Test 4: Authentication & Authorization
**Goal**: Verify auth system works

```python
from database.schema import init_db, SessionLocal, User, UserTier
from database.auth import AuthManager, RateLimiter

init_db()
db = SessionLocal()
auth = AuthManager()

# Test 1: Create user
user = auth.create_user(db, 'authtest@example.com', 'password123', 'free')
assert user is not None, 'User creation failed'
print(f'✅ User created: {user.email}')

# Test 2: Verify password
result = auth.verify_password('password123', user.password_hash)
assert result, 'Password verification failed'
print('✅ Password verification works')

# Test 3: Generate JWT token
token = auth.generate_token(user.id)
assert token is not None, 'Token generation failed'
print(f'✅ JWT token generated: {token[:20]}...')

# Test 4: Verify JWT token
verified_user_id = auth.verify_token(token)
assert verified_user_id == user.id, 'Token verification failed'
print('✅ JWT token verification works')

# Test 5: Rate limiting
limiter = RateLimiter(db, auth)
can_run, msg = limiter.can_run_simulation(user.id)
assert can_run == True, f'Rate limit failed: {msg}'
print('✅ Rate limiting works (user can run simulation)')

# Test 6: API key generation
api_key = auth.generate_api_key()
assert api_key is not None, 'API key generation failed'
print(f'✅ API key generated: {api_key[:10]}...')

db.close()
```

---

### Test 5: PDF Export
**Goal**: Verify PDF generation

```python
from export import PDFGenerator
from database.schema import init_db, SessionLocal, Simulation
import os

init_db()
db = SessionLocal()

# Get most recent simulation
sim = db.query(Simulation).order_by(Simulation.created_at.desc()).first()

if sim and sim.status == 'completed':
    gen = PDFGenerator()
    
    results = {
        'stats': {
            'starting_bankroll': sim.starting_bankroll,
            'current_bankroll': sim.final_bankroll or sim.starting_bankroll,
            'roi': sim.roi or 0,
            'win_rate': sim.win_rate or 0,
            'total_bets': sim.total_bets or 0,
            'total_wagered': sim.total_wagered or 0,
            'max_drawdown': sim.max_drawdown or 0,
            'duration_seconds': sim.duration_seconds or 0
        }
    }
    
    pdf_path = gen.generate_report(
        sim.id,
        'test@example.com',
        results,
        [],  # agent_stats
        '/tmp/test_report.pdf'
    )
    
    assert os.path.exists(pdf_path), f'PDF not created at {pdf_path}'
    size = os.path.getsize(pdf_path)
    assert size > 0, 'PDF file is empty'
    print(f'✅ PDF generated: {pdf_path} ({size} bytes)')
else:
    print('⚠️  No completed simulation found for PDF test')

db.close()
```

---

### Test 6: Web Dashboard
**Goal**: Verify HTML dashboard loads and works

```bash
# Start server
uvicorn api.main:app --host 127.0.0.1 --port 8000 &
sleep 2

# Check dashboard loads
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/static/dashboard.html)
if [ "$STATUS" = "200" ]; then
    echo "✅ Dashboard HTML loads (HTTP $STATUS)"
else
    echo "❌ Dashboard failed (HTTP $STATUS)"
fi

# Check dashboard contains expected elements
curl -s http://localhost:8000/static/dashboard.html | grep -q "Login / Register" && \
    echo "✅ Dashboard has auth section"

curl -s http://localhost:8000/static/dashboard.html | grep -q "API_URL" && \
    echo "✅ Dashboard has API integration"

pkill -f uvicorn
```

---

### Test 7: Agent Personalities
**Goal**: Verify each agent responds differently

```python
from simulation.graph import SyndicateGraph
from agents.base_agent import Game
from datetime import datetime

# Create a test game
game = Game(
    home_team='Test Home',
    away_team='Test Away',
    sport='soccer_epl',
    bookmaker='test',
    home_odds=2.0,
    away_odds=2.0,
    timestamp=datetime.now()
)

# Create syndicate and get all agents
graph = SyndicateGraph()
agents = graph.agents

print(f"✅ Found {len(agents)} agents:")
for agent in agents:
    print(f"   - {agent.name} ({agent.agent_type.value})")

# Verify agent types
agent_types = set(agent.agent_type.value for agent in agents)
expected_types = {'sharp', 'insider', 'degen', 'bookie'}
assert agent_types == expected_types, f'Unexpected agent types: {agent_types}'
print(f"✅ All agent types present: {agent_types}")
```

---

## 📊 Performance Tests

### Test 1: Simulation Speed
```bash
echo "Testing simulation speed (100 games)..."
time python main.py --games 100 --sport soccer_epl 2>&1 | tail -5
# Expected: ~60-120 seconds depending on API latency
```

### Test 2: API Response Time
```bash
time curl -s http://localhost:8000/api/dashboard \
    -H "user-id: test-user-id" > /dev/null
# Expected: < 100ms
```

### Test 3: Database Query Speed
```python
from database.schema import SessionLocal, Simulation
import time

db = SessionLocal()
start = time.time()
sims = db.query(Simulation).limit(100).all()
elapsed = time.time() - start

print(f"✅ Fetched {len(sims)} simulations in {elapsed*1000:.2f}ms")
db.close()
```

---

## 🔄 Integration Tests

### Test 1: Full User Journey
```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"journey@example.com","password":"test123"}'

# 2. View profile
curl http://localhost:8000/api/user/profile \
  -H "user-id: YOUR_USER_ID"

# 3. View dashboard
curl http://localhost:8000/api/dashboard \
  -H "user-id: YOUR_USER_ID"

# 4. Run simulation (if you add endpoint)
python main.py --games 3

# 5. View updated dashboard
curl http://localhost:8000/api/dashboard \
  -H "user-id: YOUR_USER_ID"
```

### Test 2: Error Handling
```bash
# Test 401 (no auth)
curl http://localhost:8000/api/dashboard

# Test 404 (bad user)
curl http://localhost:8000/api/user/profile \
  -H "user-id: nonexistent-user-id"

# Test duplicate registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"existing@example.com","password":"test123"}'
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"existing@example.com","password":"test456"}'
```

---

## 🐛 Debugging Tips

### Check Logs
```bash
tail -f logs/app.log           # Real-time logs
cat logs/app.json.log | grep simulation_id  # Search
```

### Query Database
```bash
sqlite3 bratislava.db
sqlite> SELECT COUNT(*) FROM simulations;
sqlite> SELECT id, status, roi FROM simulations LIMIT 5;
sqlite> .quit
```

### Monitor API
```bash
# Terminal 1: Start with verbose logging
python -m uvicorn api.main:app --reload --log-level debug

# Terminal 2: Make requests
curl -v http://localhost:8000/api/health
```

### Trace Simulation
```python
from simulation.graph import run_simulation
from data.odds_aggregator import OddsAggregator

odds = OddsAggregator()
games = odds.get_all_odds('soccer_epl')[:1]

results = run_simulation(
    games=games,
    num_games=1,
    starting_bankroll=10000,
    monitor=None,
    db=None,  # Skip DB to debug faster
    user_id=None,
    simulation_id=None
)

print(results['stats'])
```

---

## ✅ Test Checklist

- [ ] CLI simulation completes successfully
- [ ] API server starts without errors
- [ ] User registration works
- [ ] Dashboard loads in browser
- [ ] Database saves simulations
- [ ] PDF generation works
- [ ] Rate limiting enforces tier limits
- [ ] JWT tokens verify correctly
- [ ] Agent debate output is coherent
- [ ] Bankroll calculations are accurate
- [ ] No console errors or warnings
- [ ] Response times are acceptable
- [ ] Database queries complete quickly
- [ ] All 10 agents participate in debate
- [ ] Bet outcomes match expected patterns

---

**Last Updated**: November 25, 2025  
**Test Coverage**: ~80% (core features covered, edge cases need work)  
**Automation**: Ready for CI/CD integration
