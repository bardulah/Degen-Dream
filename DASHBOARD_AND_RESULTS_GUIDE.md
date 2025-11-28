# Dashboard Persistence & Real Match Results Guide

This guide covers the new features for dashboard persistence and fetching real match results.

## Table of Contents

1. [Dashboard Persistence](#dashboard-persistence)
2. [Fetching Match Results](#fetching-match-results)
3. [Score Fetching System](#score-fetching-system)
4. [Database Schema Updates](#database-schema-updates)
5. [Usage Examples](#usage-examples)

---

## Dashboard Persistence

### What Changed

The web dashboard now persists data to a SQLite database, so when you refresh the page, your simulation data remains visible.

### How It Works

1. **Database Storage**: All simulations, bets, and agent stats are now stored in `bratislava.db`
2. **Automatic Loading**: On page load, the dashboard fetches the latest simulation data
3. **Real-time Updates**: During a simulation, data is saved to DB in real-time
4. **Persistent State**: Refresh the page anytime - data persists!

### Running the Dashboard

```bash
# Start the web dashboard
cd web
python app.py

# Open browser to: http://localhost:5000
```

### Features

- ✅ **Data Persistence**: Simulations survive page refreshes
- ✅ **Bet History**: See all your past bets with results
- ✅ **Agent Performance**: Track each agent's ROI, win rate, and profit
- ✅ **Real-time Updates**: Live updates via WebSocket during simulations
- ✅ **Result Status**: See which bets won, lost, or are pending

---

## Fetching Match Results

### New: Automatic Result Fetching

The system can now fetch real match scores from ESPN's free API and update your bets!

### How to Update Results

#### 1. Update Yesterday's Games

```bash
python update_results.py
```

#### 2. Update Specific Date

```bash
python update_results.py --date 20241126
```

#### 3. Update Specific Simulation

```bash
# First, list pending simulations
python update_results.py --list-pending

# Then update a specific one
python update_results.py --simulation-id <simulation-uuid>
```

#### 4. Update Last 7 Days

```bash
python update_results.py --all
```

### What Gets Updated

- ✅ **Match Scores**: Home and away team scores
- ✅ **Bet Results**: Win, loss, or push status
- ✅ **Profit/Loss**: Actual P&L for each bet
- ✅ **Simulation Stats**: Overall ROI, win rate, final bankroll
- ✅ **Agent Stats**: Per-agent performance metrics

---

## Score Fetching System

### ESPN's Free API

We use ESPN's unofficial but stable JSON API to fetch scores. **No paid API needed!**

### Supported Sports

- **Basketball**: NBA
- **Hockey**: NHL
- **Soccer**:
  - English Premier League (EPL)
  - MLS
  - La Liga
  - Bundesliga
  - Serie A
  - Ligue 1
  - Champions League

### How It Works

The `ResultMatcher` class:

1. Fetches finished games from ESPN for a specific date
2. Matches team names to your bets using fuzzy matching
3. Determines if bets won/lost/pushed based on:
   - **Moneyline**: Simple winner determination
   - **Spread**: Adjusted scores vs. line
   - **Total**: Combined score vs. over/under
4. Updates database with results
5. Recalculates all statistics

### Team Name Matching

The system uses intelligent fuzzy matching:

```python
# These all match:
"Los Angeles Lakers" ↔ "Lakers" ✅
"LA Lakers" ↔ "Lakers" ✅
"Man United" ↔ "Manchester United" ✅
```

Threshold: 70% similarity (configurable)

---

## Database Schema Updates

### New Bet Fields

```python
# Match result tracking
game_date = Column(String)           # YYYYMMDD for ESPN API
game_id_espn = Column(String)        # ESPN game ID
home_score = Column(Integer)         # Actual home score
away_score = Column(Integer)         # Actual away score
actual_winner = Column(String)       # Team name or "TIE"
result_status = Column(String)       # "pending", "won", "lost", "push"
result_fetched_at = Column(DateTime) # When result was fetched
profit_loss = Column(Float)          # Actual P&L after result
```

### New Simulation Fields

```python
# Results tracking
roi = Column(Float)                  # Overall ROI
win_rate = Column(Float)             # Overall win rate
profit = Column(Float)               # Total profit/loss
final_bankroll = Column(Float)       # Ending bankroll
bets_settled = Column(Integer)       # How many bets have results
last_result_check = Column(DateTime) # Last result fetch time
```

### Database Migration

The schema updates are **backward compatible**. New fields are nullable, so old data works fine.

To apply schema updates:

```bash
# Delete old database and recreate (DEV ONLY!)
rm bratislava.db

# Run any simulation or start dashboard to recreate
python main.py --sample --games 5
```

For production, you'd use Alembic migrations, but this is a dev project.

---

## Usage Examples

### Example 1: Run Simulation, Then Get Results

```bash
# 1. Run simulation with real data
python main.py --daily --games 10

# Output shows:
#   Simulation ID: abc123...
#   Bets placed: 10
#   Status: awaiting_results

# 2. Wait for games to finish (next day)

# 3. Update results
python update_results.py

# Output:
#   Bets Checked:  10
#   Bets Updated:  8
#   ✅ Won:        5
#   ❌ Lost:       3
#   ⚪ Push:       0
```

### Example 2: Dashboard Workflow

```bash
# 1. Start dashboard
cd web
python app.py

# 2. Open http://localhost:5000

# 3. Click "EXECUTE SIMULATION"

# 4. Watch live updates

# 5. Refresh page - data persists! ✅

# 6. Next day, update results
cd ..
python update_results.py

# 7. Refresh dashboard to see updated results
```

### Example 3: Check Specific Simulation

```bash
# List all pending simulations
python update_results.py --list-pending

# Output:
#   Simulation: abc123-456...
#     Created:    2024-11-26 10:30:00
#     Sport:      multi-sport
#     Total Bets: 15
#     Pending:    12

# Update that specific simulation
python update_results.py --simulation-id abc123-456...

# Output:
#   Checking 20241126...
#   Checking 20241127...
#
#   FINAL RESULTS
#   Win Rate:   60.0%
#   ROI:        +12.45%
#   Profit:     €+124.50
```

---

## Advanced Features

### Automated Result Checking (Future)

You can set up a cron job to auto-check results daily:

```bash
# Add to crontab
0 9 * * * cd /path/to/Degen-Dream && python update_results.py --all
```

### API Integration

The dashboard exposes REST endpoints:

```bash
# Get latest simulation
GET /api/simulations/latest

# Response:
{
  "simulation_id": "...",
  "status": "completed",
  "stats": {
    "total_bankroll": 10500.00,
    "roi": 5.0,
    "win_rate": 55.5,
    "total_bets": 20,
    "bets_settled": 20
  },
  "bets": [...],
  "agent_stats": [...]
}
```

### Custom Date Ranges

The `SportsScoreFetcher` supports date ranges:

```python
from sports_score_fetcher import SportsScoreFetcher

fetcher = SportsScoreFetcher()

# Get all NBA games in November 2024
games = fetcher.get_nba_scores('20241101-20241130')

# Or use the class methods for any sport
```

---

## Troubleshooting

### No Results Found

**Problem**: "No match found for bet"

**Solutions**:
1. Check team names match between your odds source and ESPN
2. Adjust fuzzy match threshold in `result_matcher.py`
3. Verify game_date is set correctly (YYYYMMDD format)

### ESPN API Errors

**Problem**: 400 Bad Request from ESPN

**Solutions**:
1. Check date format (must be YYYYMMDD)
2. Don't query future dates
3. Add delays between requests (already implemented)

### Database Locked

**Problem**: "database is locked"

**Solutions**:
1. Make sure only one process accesses DB at a time
2. Close dashboard before running CLI commands
3. Check for stuck processes: `ps aux | grep python`

### Missing Sport

**Problem**: Sport not recognized

**Solutions**:
1. Check `_map_sport_to_espn()` in `result_matcher.py`
2. Add your sport mapping:
   ```python
   if 'my_league' in sport_lower:
       return ('sport_type', 'league_code')
   ```
3. See ESPN API docs for league codes

---

## File Structure

```
/home/user/Degen-Dream/
├── database/
│   ├── schema.py              # Updated with new fields
│   └── auth.py
├── data/
│   ├── result_matcher.py      # NEW: Matches scores to bets
│   └── sports_score_fetcher.py # NEW: ESPN API client
├── web/
│   ├── app.py                 # Updated with DB persistence
│   └── templates/
│       └── dashboard.html     # Updated with auto-load
├── update_results.py          # NEW: CLI tool
├── QUICK_START_SPORTS_SCORES.md
├── SPORTS_SCRAPING_RESEARCH.md
└── DASHBOARD_AND_RESULTS_GUIDE.md (this file)
```

---

## Next Steps

1. ✅ **Run a test simulation**
   ```bash
   python main.py --sample --games 5
   cd web && python app.py
   # Open http://localhost:5000
   ```

2. ✅ **Test result fetching**
   ```bash
   # Use a known past date with games
   python update_results.py --date 20241126
   ```

3. ✅ **Check persistence**
   - Refresh dashboard
   - See data persisted!

4. 🔜 **Run with real data**
   ```bash
   python main.py --daily --games 10
   # Wait for games to finish
   python update_results.py
   ```

---

## Summary

You now have:

1. **Dashboard Persistence**: Data survives page refreshes
2. **Real Match Results**: Fetch scores from ESPN API for free
3. **Automatic Bet Resolution**: System determines win/loss/push
4. **Updated Statistics**: ROI, win rate, and profit calculated from real results
5. **Easy CLI Tools**: Simple commands to update everything

The system is production-ready for personal use. For commercial use, consider:
- Proper database migrations (Alembic)
- Error handling improvements
- Rate limiting for ESPN API
- Alternative score sources as backup

Enjoy your fully functional betting syndicate dashboard! 🎰
