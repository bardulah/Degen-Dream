# Quick Start Guide

## Daily Simulation with Email

### 1. Configure Email (Optional)

```bash
# Get Gmail App Password from: https://myaccount.google.com/apppasswords
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="xxxx xxxx xxxx xxxx"
```

### 2. Run Daily Simulation

```bash
# Analyze today's matches and send email report
python main.py --daily --games 10

# Output:
# ✅ Fetches live odds from Nike.sk
# ✅ Runs agent analysis on each game
# ✅ Collects consensus predictions
# ✅ Sends email report with picks
# ✅ Stores bets in database for next-day result matching
```

### 3. Schedule Daily Runs

```bash
# Run every day at 8:00 AM UTC
python scheduler.py --time 08:00

# Run at specific time (24-hour format):
python scheduler.py --time 18:00
```

## What Happens

### Per-Game Analysis
1. **Gemini Search** - Fetch real-time team news, injuries, form
2. **Agent Analysis** - 10 agents evaluate the match
   - 3 Sharp agents (statistical arbitrage)
   - 2 Insider agents (rumors, team intel)
   - 3 Degen agents (aggressive plays)
   - 2 Bookie agents (line movement)
3. **Debate** - Agents argue for/against bets
4. **Consensus** - Vote on final consensus pick
5. **Bet Placed** - Store in database

### Email Report
Contains:
- Summary stats (sport, games, total wagered)
- All predictions with confidence levels
- Status: "Results Pending"

### Result Matching (Next Day)
1. Fetch actual match scores
2. Match predictions to outcomes
3. Calculate performance metrics
4. Update agent stats
5. Send follow-up report with ROI, win rate

## Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point with email support |
| `notification/email_sender.py` | Email notifications |
| `data/daily_odds_fetcher.py` | Fetch today's odds only |
| `scheduler.py` | Schedule daily runs |
| `EMAIL_SETUP.md` | Email configuration guide |
| `SAMPLE_EMAIL.html` | Email template example |

## Example Run

```bash
$ python main.py --daily --games 5

📡 Fetching odds data...
📅 Fetching SOCCER for today...
✓ Nike.sk: 39 games

🎰 BRATISLAVA BETTING SYNDICATE - ANALYSIS START
🔍 Gemini Search enabled

📊 GAME 1/5
Chelsea vs FC Barcelona
✅ Consensus: Chelsea (Jozef) €95.45 | 95% confidence
✅ BET PLACED

📊 GAME 2/5
Arsenal vs Bayern
... (analysis)

======================================================================
🎰 ANALYSIS COMPLETE
📊 Predictions Collected: 5 games
💾 Stored in database for real result matching
⏳ Waiting for actual match results (end of day/next day)

📧 Sending email report...
✅ Email sent to cli_user@bratislava.local

💡 TIP: Run 'streamlit run gui/streamlit_app.py' for interactive GUI
📧 TIP: Configure email with: export SENDER_EMAIL='...' SENDER_PASSWORD='...'
```

## Database

All predictions stored in SQLite (bratislava.db):
- Simulation record
- Individual bets with:
  - Game info
  - Consensus pick
  - Stake
  - Confidence
  - Status: PENDING (awaiting real result)

Query:
```python
from database.schema import SessionLocal, Simulation, Bet

db = SessionLocal()
sim = db.query(Simulation).order_by(Simulation.created_at.desc()).first()
bets = db.query(Bet).filter(Bet.simulation_id == sim.id).all()

for bet in bets:
    print(f"{bet.bet_team} | €{bet.stake} | {bet.confidence}%")
```

## Next: Match Results

After matches play (end-of-day or next day):

```bash
python scripts/fetch_results.py --date 2025-11-25

# Will:
# 1. Fetch actual match scores
# 2. Match against predictions
# 3. Calculate ROI, win rate, etc
# 4. Send results email
# 5. Update simulation record
```

## Tips

- **Nike.sk** works best during betting hours (11 AM - 11 PM CET)
- **Gemini Search** requires GOOGLE_API_KEY (optional, app works without)
- **Email** optional - app runs fine without it
- **More games = Longer analysis** - Use --games 5-10 for testing, 20+ for production

## Troubleshooting

**No games fetched?**
```bash
python -c "from data.daily_odds_fetcher import DailyOddsFetcher; DailyOddsFetcher().get_todays_games()"
```

**Email not sending?**
```bash
python -c "from notification.email_sender import EmailSender; s=EmailSender(); print('Enabled' if s.enabled else 'Not configured')"
```

**Check logs:**
```bash
tail -f logs/app.log
tail -f logs/app.json.log  # Machine-readable
```

## Architecture

```
Nike.sk Scraper ────┐
                    ├──→ DailyOddsFetcher ──→ Agent Analysis ──→ Email Report
OddsAPI Client ─────┘                              │
                                                  DBL
                                           (Predictions Stored)
                                                   │
                                          (Next day/end-of-day)
                                                   │
                                         Fetch Real Results ──→ Result Matching ──→ Final Report
```
