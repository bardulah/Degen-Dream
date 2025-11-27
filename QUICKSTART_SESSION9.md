# Session 9: Results Matching & Agent Leaderboard

## Quick Start (5 mins)

```bash
# 1. Run a simulation
python main.py --games 3 --sample --no-live

# 2. Check agent leaderboard
python main.py --leaderboard

# 3. View upcoming results matching (experimental)
python main.py --update-results
```

## What's New

### 1. Agent Leaderboard (`--leaderboard`)
Shows agent performance metrics from all past simulations:
- **ROI**: Return on investment (profit/bankroll)
- **Win Rate**: Percentage of bets that won
- **Confidence Calibration**: How well confidence predicts actual wins
- **P&L**: Total profit or loss

```
🥇 Lucia
   💰 ROI: +5.56% | Win Rate: 50.0% | Confidence: 95%
   📊 5W-5L | Profit: €+38.71
   📈 Calibration Error: 0.45
```

### 2. Results Matching (Experimental)
**Status**: Infrastructure built, API fetching not implemented yet

The system has:
- ✅ `results_matcher.py` - Fuzzy matches real scores with bets
- ✅ `results_updater.py` - Updates database with outcomes
- ✅ `--update-results` command
- ⏳ Actual score fetching from APIs (needs external data source)

To use this feature when ready:
1. Get real match scores from Flashscore/ESPN/OddsAPI
2. Run: `python main.py --update-results --date 2025-11-27`
3. System will match bets, settle them, and calculate P&L

### 3. Database Schema Ready
Bets now store:
- `outcome`: PENDING, WON, LOST, PUSH
- `profit_loss`: €amount for each settled bet
- Agent accuracy tracked: wins, losses, ROI per agent

## Next Steps

### Immediate (2-3 hours)
1. **Connect to real score API**
   - Nike.sk scraper (can extract scores)
   - Flashscore API (if available)
   - ESPN (has historical scores)
   - OddsAPI (in-play markets)

2. **Implement match fetching**
   - `ResultsMatcher.fetch_today_results()`
   - `ResultsMatcher.fetch_results_for_date(date)`
   - Handle team name variations

3. **Test end-to-end**
   - Run simulation
   - Get real scores
   - Settle bets
   - Check leaderboard

### Later (1-2 hours)
1. **Discord leaderboard notifications**
   - Post daily stats to channel
   - Show top agents and predictions
   - Monthly ROI tracking

2. **Enhanced Discord integration**
   - Better result formatting
   - Embed game odds at bet time
   - Show voting vs Oracle comparison

## Architecture

```
Simulation Run
    ↓
10 agents analyze games
    ↓
Betting decisions stored as PENDING
    ↓
EmailSender notifies with picks
    ↓
DiscordNotifier sends alerts
    ↓
[LATER] ResultsMatcher fetches real scores
    ↓
ResultsUpdater matches and settles bets
    ↓
Agent accuracy tracked
    ↓
--leaderboard shows performance
```

## Code Example: Using ResultsUpdater

```python
from database.results_updater import ResultsUpdater
from database.schema import SessionLocal
from agents.base_agent import Game

# Initialize
db_url = "sqlite:///bratislava.db"
updater = ResultsUpdater(db_url)

# Get real results (TODO: from API)
game_results = [
    Game(id="g1", home_team="Barcelona", away_team="Real Madrid", 
         home_score=2, away_score=1, ...),
    # ... more games
]

# Update database
stats = updater.update_pending_bets(game_results)
print(f"Updated: {stats['updated']} bets")
print(f"Wins: {stats['wins']}, Losses: {stats['losses']}")
print(f"P&L: €{stats['total_profit'] - stats['total_loss']:.2f}")

# Show leaderboard
updater.print_leaderboard(days=7)
```

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `data/results_matcher.py` | Match scores with bets | ✅ Complete |
| `database/results_updater.py` | Update DB with results | ✅ Complete |
| `main.py` | CLI commands | ✅ Complete |
| `--leaderboard` command | Show agent stats | ✅ Working |
| `--update-results` command | Placeholder for future | ⏳ Needs API |

## Testing

```bash
# Test leaderboard with existing data
python main.py --leaderboard

# Run 3 games and check database
python main.py --games 3 --sample --no-live

# Check if bets were saved
sqlite3 bratislava.db "SELECT COUNT(*) FROM bets WHERE outcome='pending';"
```

## Notes

- All bets saved with status PENDING until matches end
- Agent accuracy tracked automatically
- No manual setup needed for database
- Results matching will be automatic when API is connected
- Leaderboard shows cumulative stats across all simulations
