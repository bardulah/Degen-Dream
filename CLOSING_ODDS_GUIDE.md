# Closing Odds Fetching - Implementation Guide

## The Challenge You Identified

You're absolutely right - fetching closing odds is more complex than it first appears:

1. **You need game start times** - to know when to fetch
2. **You need to fetch RIGHT before games start** - not hours before, not during the game
3. **You need continuous monitoring** - games start at different times throughout the day

This can't be a simple one-time script - it requires scheduling and automation.

---

## Two Implementation Approaches

### ⚡ Approach 1: Scheduled Pre-Game Fetching (Recommended)

**How it works:**
1. Every hour, check for games starting in next 2 hours
2. Schedule a job to fetch odds 10 minutes before each game
3. Store those as "closing odds"
4. Update all bets for that game with CLV

**Pros:**
- ✅ Lighter on API calls (~5-10 calls per game)
- ✅ Simpler to implement and maintain
- ✅ Good enough accuracy (closing line is stable in final 10 minutes)
- ✅ Easy to debug and monitor

**Cons:**
- ❌ Not perfectly accurate (closing line could shift in final 10 min)
- ❌ Misses very late line movements

**Implementation:** `analytics/closing_odds_fetcher.py` (ClosingOddsFetcher class)

**Usage:**
```bash
# Run as daemon (starts scheduler)
python -m analytics.closing_odds_fetcher --daemon
```

**How the scheduler works:**
```python
# Runs continuously in background
while True:
    # Every hour: Check for upcoming games
    upcoming = get_upcoming_games(hours_ahead=2)

    # For each game starting in next 2 hours:
    for game in upcoming:
        # Schedule odds fetch 10 min before game
        fetch_time = game.start_time - 10 minutes
        schedule_job(fetch_closing_odds, run_at=fetch_time)

    time.sleep(3600)  # Wait 1 hour, repeat
```

**Workflow Example:**
```
10:00 AM - Scheduler checks upcoming games
           Finds: Lakers vs Warriors at 7:00 PM
           Schedules: Fetch closing odds at 6:50 PM

6:50 PM  - Fetch current Lakers/Warriors odds
           Store: Lakers 2.05 / Warriors 1.85 (closing line)
           Update all Lakers/Warriors bets with CLV

7:00 PM  - Game starts (odds are locked)
```

---

### 📊 Approach 2: Continuous Polling with History (Most Accurate)

**How it works:**
1. Poll odds API every 30 minutes ALL DAY
2. Store EVERY odds snapshot in `odds_history` table
3. When game starts, grab the LAST record before game started
4. That's your true closing line

**Pros:**
- ✅ Most accurate closing line (literally the last odds before game)
- ✅ Full historical data (can analyze line movements)
- ✅ Can backfill if you miss a fetch

**Cons:**
- ❌ Heavy on API calls (48 calls per day per game)
- ❌ More database storage needed
- ❌ More complex to maintain

**Implementation:** `analytics/closing_odds_fetcher.py` (ContinuousOddsPoller class)

**Database Schema:**
```python
class OddsHistory(Base):
    id = UUID
    game_id = ESPN game ID
    home_odds = 2.05
    away_odds = 1.85
    fetched_at = 2025-01-15 18:45:00  # Timestamp of fetch
```

**Example Data:**
```
Lakers vs Warriors (game starts 7:00 PM):

fetched_at          | home_odds | away_odds
--------------------|-----------|----------
12:00 PM           | 2.15      | 1.75
12:30 PM           | 2.12      | 1.78
1:00 PM            | 2.10      | 1.80
...
6:30 PM            | 2.08      | 1.82
6:50 PM            | 2.05      | 1.85     ← CLOSING LINE (last before 7pm)
7:00 PM            | GAME STARTED, ODDS LOCKED
```

**Usage:**
```python
# Start continuous poller
poller = ContinuousOddsPoller(poll_interval_minutes=30)

# Run as daemon
while True:
    poller.poll_and_store_odds()  # Fetch and store current odds
    time.sleep(1800)  # Wait 30 min

# Later, get closing odds for a game
closing = poller.get_closing_odds_from_history(game_id='401584889')
# Returns: {home_odds: 2.05, away_odds: 1.85}
```

---

## Which Approach Should You Use?

### Start with Approach 1 (Scheduled)

**Reasons:**
1. **Good enough for CLV tracking** - Closing line is stable in final 10 minutes
2. **Way lighter on API calls** - Won't hit rate limits
3. **Simpler to debug** - Less moving parts
4. **Professional bettors use this** - Most CLV trackers use "pre-game snapshot"

### Upgrade to Approach 2 Later If:
- You want to analyze line movements over time
- You're doing advanced steam/reverse line movement tracking
- You have unlimited API access
- You need academic-level accuracy

---

## Implementation Steps (Approach 1)

### 1. Install Dependencies

```bash
pip install schedule
```

### 2. Set Up the Scheduler

```bash
# Test it first
python -m analytics.closing_odds_fetcher

# Output:
# Found 8 upcoming games in next 24 hours:
#   Lakers vs Warriors - Starts in 420 minutes
#   Celtics vs Heat - Starts in 450 minutes
#   ...
```

### 3. Run as Daemon (Background Service)

```bash
# Run in background
nohup python -m analytics.closing_odds_fetcher --daemon > logs/closing_odds.log 2>&1 &
```

Or use systemd (Linux):

```ini
# /etc/systemd/system/closing-odds.service
[Unit]
Description=Closing Odds Fetcher
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/user/Degen-Dream
ExecStart=/usr/bin/python3 -m analytics.closing_odds_fetcher --daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable closing-odds
sudo systemctl start closing-odds
sudo systemctl status closing-odds
```

### 4. Monitor Logs

```bash
# Check if it's working
tail -f logs/closing_odds.log

# You should see:
# Checking for upcoming games...
# Found 3 games starting in next 2 hours
# Scheduled closing odds fetch for Lakers vs Warriors in 112.5 minutes
# ...
# Fetching closing odds for Lakers vs Warriors
# ✅ Stored closing odds: Lakers 2.05 / Warriors 1.85
# Updated 3 bets with closing odds for game 401584889
```

---

## How It Integrates with CLV Tracker

Once closing odds are fetched, the CLV tracker automatically calculates:

```python
# Your bet
bet_odds = 2.15  # You bet Lakers at 2.15

# Closing line (fetched 10 min before game)
closing_odds = 2.05

# CLV calculation
clv = ((2.15 - 2.05) / 2.05) * 100 = +4.88% CLV ✅
```

**Database updates:**
```python
bet.closing_odds = 2.05
bet.clv_percentage = +4.88
bet.beat_closing_line = True  # You got better odds than closing
```

**Then after game finishes:**
```python
bet.result_status = 'won'  # Lakers won
bet.profit_loss = +115.00  # €100 × (2.15 - 1) = €115
```

**CLV Validation:**
```python
# Analyze if positive CLV = winning bets
tracker.analyze_clv_vs_results()

# Output:
{
    'positive_clv': {
        'total': 47,
        'wins': 28,
        'win_rate': 59.6%  # Beating closing line = winning long-term ✅
    },
    'negative_clv': {
        'total': 23,
        'wins': 9,
        'win_rate': 39.1%  # Losing to closing line = losing long-term ❌
    }
}
```

---

## Key Technical Details

### Game Time Detection

ESPN API provides game times in ISO 8601 format:

```python
event['date'] = "2025-01-15T19:00:00Z"  # 7:00 PM UTC

# Convert to local timezone
game_time = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))

# Calculate time until game
now = datetime.now()
hours_until = (game_time - now).total_seconds() / 3600

if 0 < hours_until <= 2:
    # Game starting in next 2 hours
    schedule_closing_odds_fetch(game, minutes_before=10)
```

### Avoiding Duplicate Scheduling

```python
# Track which games are already scheduled
self.scheduled_games = set()

def schedule_closing_odds_fetch(self, game):
    game_id = game['game_id']

    # Don't schedule twice
    if game_id in self.scheduled_games:
        return

    # Schedule job
    schedule.every(seconds_until_fetch).seconds.do(
        self.fetch_closing_odds, game_id=game_id
    )

    self.scheduled_games.add(game_id)
```

### Error Handling

```python
try:
    closing_odds = self.odds_client.fetch_live_odds(sport='nba')
except Exception as e:
    logger.error(f"Failed to fetch closing odds: {e}")
    # Fallback: Try secondary source
    try:
        closing_odds = self.sofascore.get_odds(game_id)
    except:
        logger.error("All sources failed, CLV not available for this game")
        return
```

---

## API Call Optimization

### Approach 1 API Usage

For a typical day with 10 NBA games:

```
Hourly checks:         24 × 1 = 24 calls
Closing odds fetches:  10 × 1 = 10 calls
Total:                        34 calls/day
```

**Cost:** Minimal (well within free tier of most APIs)

### Approach 2 API Usage

```
Polls every 30 min:    48 × 1 = 48 calls
Per game tracking:     10 games × 48 = 480 data points stored
Total:                        48 calls/day
```

**Storage:** ~1MB per day of historical odds data

---

## Testing the System

### 1. Test Game Detection

```python
from analytics.closing_odds_fetcher import ClosingOddsFetcher

fetcher = ClosingOddsFetcher()
upcoming = fetcher.get_upcoming_games(hours_ahead=24)

for game in upcoming:
    print(f"{game['home_team']} vs {game['away_team']}")
    print(f"  Starts: {game['start_time']}")
    print(f"  Minutes until: {game['minutes_until_start']:.0f}")
```

### 2. Test Closing Odds Fetch

```python
# Manually fetch closing odds for a game
fetcher.fetch_and_store_closing_odds(
    game_id='401584889',
    sport='nba',
    home_team='Lakers',
    away_team='Warriors'
)

# Check database
bets = db.query(Bet).filter(Bet.game_id_espn == '401584889').all()
for bet in bets:
    print(f"Bet: {bet.bet_team} @ {bet.odds}")
    print(f"Closing: {bet.closing_odds}")
    print(f"CLV: {bet.clv_percentage:+.2f}%")
```

### 3. Test Full Workflow

```bash
# Terminal 1: Run scheduler
python -m analytics.closing_odds_fetcher --daemon

# Terminal 2: Monitor logs
tail -f logs/closing_odds.log

# Terminal 3: Check database
python -c "from analytics.clv_tracker import CLVTracker; CLVTracker().get_clv_stats()"
```

---

## Troubleshooting

### Issue: No upcoming games found

**Cause:** ESPN API might not have tomorrow's schedule yet

**Solution:** ESPN usually posts schedules 24-48 hours ahead. Check again later.

```python
# Verify ESPN has the schedule
import requests
url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
response = requests.get(url, params={'dates': '20250116'})
print(response.json())  # Should show games if available
```

### Issue: Closing odds not updating bets

**Cause:** Team name mismatch (ESPN: "LA Lakers" vs Odds API: "Lakers")

**Solution:** Use fuzzy matching in `_update_bets_with_closing_odds`

```python
from difflib import SequenceMatcher

def match_team_name(espn_name, odds_name):
    ratio = SequenceMatcher(None, espn_name, odds_name).ratio()
    return ratio > 0.7  # 70% similarity
```

### Issue: Scheduler stops running

**Cause:** Unhandled exception in scheduled job

**Solution:** Wrap jobs in try/except

```python
def safe_fetch_closing_odds(*args, **kwargs):
    try:
        self.fetch_closing_odds(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in scheduled job: {e}")
        # Continue running
```

---

## Next Steps

1. **Test the scheduler** with upcoming games
2. **Let it run for a week** to collect CLV data
3. **Analyze results** with `clv_tracker.analyze_clv_vs_results()`
4. **Validate your edge** - Positive CLV = long-term profit 📈

The closing odds fetcher is now fully implemented and ready to use!
