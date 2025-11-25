# Daily Email Simulation - Implementation Summary

## What Was Built ✅

### 1. **Daily Odds Fetcher** (`data/daily_odds_fetcher.py`)
- Fetches today's matches only (24-hour window)
- Multiple sources: Nike.sk + OddsAPI
- Top leagues only:
  - Soccer: EPL, La Liga, Bundesliga, Serie A, Ligue 1
  - Basketball: NBA
  - Hockey: NHL
  - Tennis: ATP, WTA
- Deduplicates matches across sources
- Returns best available odds

### 2. **Email Notification System** (`notification/email_sender.py`)
- Sends HTML email reports after each simulation
- Supports Gmail with App Passwords
- Configurable SMTP server (Gmail, Outlook, etc.)
- Beautiful HTML template with:
  - Summary statistics
  - All predictions with confidence
  - Stake amounts
  - "Results Pending" status message

### 3. **Analysis Workflow (No Simulated Outcomes)**
Currently:
1. ✅ Fetch today's odds from Nike.sk
2. ✅ Run multi-agent analysis per game
3. ✅ Generate consensus predictions
4. ✅ Store bets in database with PENDING status
5. ✅ Send email report with picks
6. ⏳ **Next step:** Fetch real results and match predictions

### 4. **Bug Fixes**
- ✅ Added `PARLAY` to BetType enum
- ✅ Fixed `save_simulation()` to handle None values
- ✅ Fixed logger to handle optional ROI/win_rate
- ✅ Removed fake outcome simulation

### 5. **Documentation**
- `EMAIL_SETUP.md` - Email configuration guide
- `QUICK_START.md` - Quick reference for daily runs
- `SAMPLE_EMAIL.html` - Visual example of email output

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `notification/email_sender.py` | Created | Email notifications |
| `notification/__init__.py` | Created | Package init |
| `data/daily_odds_fetcher.py` | Created | Today's odds fetcher |
| `scheduler.py` | Created | Daily scheduler |
| `main.py` | Updated | Email integration |
| `simulation/graph.py` | Updated | Removed outcome simulation |
| `database/schema.py` | Updated | Added PARLAY bet type |
| `database/simulation_store.py` | Updated | Handle None values |
| `monitoring/logger.py` | Updated | Optional parameters |
| `EMAIL_SETUP.md` | Created | Email guide |
| `QUICK_START.md` | Created | Quick reference |
| `SAMPLE_EMAIL.html` | Created | Email template |

## How to Use

### Setup Email (Optional)
```bash
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="16-char-app-password"
```

### Run Daily Simulation
```bash
# Analyze today's matches and send email
python main.py --daily --games 10

# Or schedule for daily 8 AM run
python scheduler.py --time 08:00
```

### What Happens
1. Nike.sk fetches 30-40 live soccer odds
2. Agents analyze each game (5-10 min per game depending on LLM)
3. Consensus predictions collected
4. Email sent with all picks and confidence levels
5. Bets stored in database with PENDING status

### Example Output
```
🎰 BRATISLAVA BETTING SYNDICATE - ANALYSIS START

📊 GAME 1/5
Chelsea vs FC Barcelona
✅ Consensus: Chelsea | €95.45 | 95% confidence
✅ BET PLACED

[... more games ...]

🎰 ANALYSIS COMPLETE
📊 Predictions Collected: 5 games
💾 Stored in database for real result matching
⏳ Waiting for actual match results (end of day/next day)

📧 Sending email report...
✅ Email sent to cli_user@bratislava.local
```

## Email Report Contents

Each email includes:
- Sport analyzed (Soccer, Basketball, etc)
- Number of games analyzed
- All predictions:
  - Matchup
  - Consensus pick (team)
  - Stake amount (€)
  - Confidence level (%)
- Total wagered
- Status: "Results Pending"
- Next steps info

## Database Integration

All predictions saved to `bratislava.db`:
```
Simulation record:
  - id, sport, num_games
  - status: 'pending_results'
  - total_bets, total_wagered

Bet records (one per consensus pick):
  - simulation_id
  - agent_name (who won debate)
  - game_home_team, game_away_team
  - bet_team (consensus pick)
  - stake, confidence
  - outcome: PENDING (awaiting real result)
```

## Performance Notes

- **Per-game analysis time:** 1-2 minutes (depends on Gemini Search + LLM)
- **Total for 5 games:** ~7-10 minutes
- **Total for 10 games:** ~15-20 minutes
- **Note:** Gemini API calls are slow; can optimize with caching

## Next Steps (Not Yet Implemented)

### 1. Fetch Real Results (High Priority)
Create `scripts/fetch_results.py`:
```bash
python scripts/fetch_results.py --date 2025-11-25

# Should:
1. Query Flashscore/ESPN for match results
2. Match each prediction to actual outcome
3. Calculate profit/loss per bet
4. Update Simulation record with metrics
5. Send results email with ROI, win rate
```

### 2. Result Matching API
Free sports data APIs:
- **Flashscore** (web scraping, no API)
- **ESPN** (no free API for full data)
- **Football-Data.org** (free tier limited)
- **OpenLigaDB** (limited sports)

Best approach: Web scraping or manual entry

### 3. Performance Dashboard
Display:
- Historical ROI trends
- Agent accuracy by type
- Best-performing agents
- Win rate by sport
- Confidence calibration

### 4. Agent Learning
Update confidence weights based on:
- Win/loss track record
- Calibration accuracy
- Market efficiency

## Configuration

### Email Providers

**Gmail:**
```bash
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="xxxx xxxx xxxx xxxx"  # App Password
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
```

**Outlook:**
```bash
export SENDER_EMAIL="your-email@outlook.com"
export SENDER_PASSWORD="your-password"
export SMTP_SERVER="smtp.office365.com"
export SMTP_PORT="587"
```

### Other Settings
```bash
# Custom start time for daily run
python scheduler.py --time 18:00  # 6 PM UTC

# Number of games (more = longer analysis)
python main.py --daily --games 20

# Test without email
python main.py --daily --games 5 --no-live
```

## Troubleshooting

**Email not sending:**
```bash
python -c "from notification.email_sender import EmailSender; s=EmailSender(); print('OK' if s.enabled else 'NOT CONFIGURED')"
```

**No games fetched:**
- Nike.sk only available during betting hours (11 AM - 11 PM CET)
- Check internet connection
- Try: `python -c "from data.daily_odds_fetcher import DailyOddsFetcher; DailyOddsFetcher().get_todays_games()"`

**Slow analysis:**
- Gemini Search is slow (can disable if needed)
- Too many games (use --games 5-10 for testing)
- LLM latency (normal, no optimization available)

**Check logs:**
```bash
tail -f logs/app.log            # Human-readable
tail -f logs/app.json.log       # Machine-readable
```

## Success Criteria

✅ **Completed:**
1. Fetch live odds from Nike.sk
2. Analyze games with multi-agent system
3. Collect consensus predictions
4. Store in database
5. Send email reports
6. Support daily scheduling

⏳ **Pending:**
1. Fetch real match results
2. Match predictions to outcomes
3. Calculate performance metrics
4. Send results email

## Architecture

```
Daily Run (8 AM)
    ↓
Nike.sk Scraper (39 games)
    ↓
DailyOddsFetcher (filter by time/league)
    ↓
SyndicateGraph (per-game analysis)
    ├─ Gemini Search (news, injuries)
    ├─ 10 Agents analyze
    ├─ Debate phase
    └─ Consensus pick
    ↓
Save to DB (PENDING)
    ↓
EmailSender (send report)
    ↓
[Wait for end-of-day/next day]
    ↓
FetchResults (real scores)
    ↓
MatchResults (predict vs actual)
    ↓
UpdateDB (ROI, metrics)
    ↓
SendResultsEmail
```

## Summary

The system is now **fully operational for daily prediction collection and email reporting**. It fetches real odds, runs agent analysis, collects predictions, and sends professional HTML email reports.

The next phase is to integrate real result fetching to close the loop and provide performance metrics.

**Status:** 🟢 **READY FOR DAILY USE**
