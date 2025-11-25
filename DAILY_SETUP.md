# Daily Simulation Setup

Run daily simulations with real odds from Nike.sk and top leagues only.

## Quick Start

### Option 1: Run Once (Today's Games)
```bash
python main.py --daily --games 10 --no-live
```

This fetches:
- **Soccer**: 30-40 games (mixed from Nike.sk + OddsAPI)
- **Basketball**: NBA games only
- **Hockey**: NHL games only
- **Tennis**: ATP/WTA matches only

Output is saved to database and can be exported as PDF.

### Option 2: Schedule Daily at Specific Time

```bash
# Run every day at 8:00 AM UTC
python scheduler.py --time 08:00

# Run every day at 6:00 PM UTC
python scheduler.py --time 18:00

# Run immediately (testing)
python scheduler.py --run-now
```

The scheduler will:
1. Run the simulation daily at the specified time
2. Use Nike.sk scraper for fresh odds
3. Only include top leagues (best odds, most activity)
4. Save results to database
5. Log all activity to `logs/`

## What Gets Fetched

### Soccer
- Nike.sk: 30-40 matches (all available)
- OddsAPI: EPL, La Liga, Bundesliga, Serie A, Ligue 1

### Basketball, Hockey, Tennis
- OddsAPI: Top leagues only
  - Basketball: NBA
  - Hockey: NHL
  - Tennis: ATP, WTA

## Date Filtering

By default, only matches within the next **24 hours** are included.

Change with:
```bash
# Fetch next 48 hours
python main.py --daily --games 50
# (modify DailyOddsFetcher call in main.py to use hours_ahead=48)
```

## Files Created/Modified

- **`data/daily_odds_fetcher.py`**: New - handles date/league filtering
- **`scheduler.py`**: New - daily task scheduler
- **`main.py`**: Updated - added `--daily` flag
- **`requirements.txt`**: Added `schedule` package

## How It Works

1. **Nike.sk Scraper** fetches current odds
   - Playwright automation (headless browser)
   - Parses game info from HTML
   - Real-time odds (no future matches)

2. **OddsAPI** fetches top leagues
   - Uses TheOddsAPI to get official odds
   - Falls back to sample data if API fails

3. **Deduplication** merges duplicate matches across sources
   - Keeps best odds for each match
   - Uses fuzzy team name matching (85% threshold)

4. **Agents analyze** using filtered set
   - Faster analysis (fewer games)
   - Focus on best matchups

5. **Results saved** to database
   - SQLite locally, PostgreSQL in production
   - Can export PDF reports

## Database

Simulations are saved to `bratislava.db` (SQLite) by default.

Query results:
```python
from database.schema import SessionLocal, Simulation
db = SessionLocal()
sims = db.query(Simulation).order_by(Simulation.created_at.desc()).limit(10).all()
for sim in sims:
    print(f"{sim.created_at}: ROI {sim.roi:.2f}%")
```

## Logs

All simulation runs are logged to:
- `logs/app.json.log` - Machine-readable (analytics, monitoring)
- `logs/app.log` - Human-readable (debugging)

## Troubleshooting

### Nike scraper fails
```bash
python -m playwright install chromium
```

### No games found
- Nike.sk only works during betting hours (usually 11 AM - 11 PM CET)
- OddsAPI requires valid API key in `.env`
- Check available sports with: `python -c "from data.odds_api import OddsAPIClient; OddsAPIClient().get_sports()"`

### Slow performance
- Nike.sk scraper takes 30-45 seconds (Playwright overhead)
- Use `--no-live` to skip live monitoring
- Reduce `--games` count for testing

## Next Steps

1. Set up daily cron job (Linux/Mac):
```bash
crontab -e
# Add line:
0 8 * * * cd /path/to/Degen-Dream && python scheduler.py --time 08:00 >> logs/scheduler.log 2>&1
```

2. Or use systemd timer (Linux):
```bash
# Create /etc/systemd/user/degen-dream.timer
# And /etc/systemd/user/degen-dream.service
# Then: systemctl --user enable degen-dream.timer
```

3. Monitor results via API:
```bash
curl http://localhost:8000/api/stats/overview
```

## API Integration

The FastAPI server provides:
- `/api/stats/overview` - Summary of last 10 simulations
- `/api/simulations/{id}` - Details of specific simulation
- `/api/simulations/{id}/export-pdf` - PDF report

Start API server:
```bash
uvicorn api.main:app --reload
```

Then access dashboard at `http://localhost:8000/api/dashboard`
