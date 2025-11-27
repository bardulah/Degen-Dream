# Quick Start Guide: Fetching Sports Scores

## TL;DR - The Answer

**Use ESPN's Hidden API** - it's the best free option for fetching finished sports scores.

- No scraping needed (it's a JSON API)
- No authentication required
- Free and reliable
- Covers NBA, NHL, and Soccer
- Just simple HTTP GET requests

## Installation

```bash
pip install requests
```

That's it. No other dependencies needed.

## Quick Usage

```python
import requests

# Get NBA scores from a specific date
date = '20241126'  # Format: YYYYMMDD
url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"
response = requests.get(url)
data = response.json()

# Print finished games
for event in data['events']:
    if event['status']['type']['completed']:
        comp = event['competitions'][0]['competitors']
        home = next(c for c in comp if c['homeAway'] == 'home')
        away = next(c for c in comp if c['homeAway'] == 'away')
        print(f"{away['team']['displayName']} {away['score']} @ {home['team']['displayName']} {home['score']}")
```

## Using the Provided Class

The repository includes a ready-to-use class in `sports_score_fetcher.py`:

```python
from sports_score_fetcher import SportsScoreFetcher

fetcher = SportsScoreFetcher()

# Get NBA scores
nba_games = fetcher.get_nba_scores('20241126')
for game in nba_games:
    print(f"{game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']}")

# Get NHL scores
nhl_games = fetcher.get_nhl_scores('20241126')

# Get Soccer scores (Premier League)
epl_games = fetcher.get_soccer_scores('eng.1', '20241123')
```

## Run the Example

```bash
python sports_score_fetcher.py
```

Note: Edit the date in the script if you want to test with a specific date.

## API Endpoints Reference

### Basketball (NBA)
```
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD
```

### Hockey (NHL)
```
https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=YYYYMMDD
```

### Soccer
```
https://site.api.espn.com/apis/site/v2/sports/soccer/{LEAGUE}/scoreboard?dates=YYYYMMDD
```

**Soccer League Codes:**
- `eng.1` - English Premier League
- `usa.1` - MLS
- `esp.1` - La Liga
- `ger.1` - Bundesliga
- `ita.1` - Serie A
- `fra.1` - Ligue 1
- `uefa.champions` - UEFA Champions League

## Date Formats

- Single date: `?dates=20241126`
- Date range: `?dates=20241101-20241130` (max 13 months)
- No date: Returns today's games

## Checking if a Game is Finished

```python
if event['status']['type']['completed']:
    # Game is finished
    status = event['status']['type']['detail']  # Usually "Final"
```

## Best Practices

1. **Add delays between requests** (1-2 seconds)
   ```python
   import time
   time.sleep(1)
   ```

2. **Handle errors gracefully**
   ```python
   try:
       response = requests.get(url, timeout=10)
       response.raise_for_status()
       data = response.json()
   except requests.exceptions.RequestException as e:
       print(f"Error: {e}")
   ```

3. **Cache results** to avoid repeated calls
   ```python
   import json

   # Save to file
   with open('scores.json', 'w') as f:
       json.dump(data, f)
   ```

## Complete Example - All Sports

```python
from sports_score_fetcher import SportsScoreFetcher
import time

fetcher = SportsScoreFetcher()
date = '20241126'

# NBA
print("NBA Games:")
for game in fetcher.get_nba_scores(date):
    print(f"  {game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']}")

time.sleep(1)  # Be respectful

# NHL
print("\nNHL Games:")
for game in fetcher.get_nhl_scores(date):
    print(f"  {game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']}")

time.sleep(1)

# Soccer (Premier League)
print("\nPremier League Games:")
for game in fetcher.get_soccer_scores('eng.1', '20241123'):  # Use weekend date for EPL
    print(f"  {game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']}")
```

## What You Get From Each Game

The parsed game info includes:

```python
{
    'game_id': '401704982',
    'date': '2024-11-26T23:00Z',
    'status': 'Final',
    'home_team': 'Washington Wizards',
    'home_abbr': 'WSH',
    'away_team': 'Chicago Bulls',
    'away_abbr': 'CHI',
    'home_score': 108,
    'away_score': 127,
    'winner': 'Chicago Bulls'
}
```

## Alternative: Direct API Calls Without the Class

If you prefer minimal code:

```python
import requests

def get_finished_games(sport, league, date):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    response = requests.get(url, params={'dates': date})
    data = response.json()

    games = []
    for event in data.get('events', []):
        if event['status']['type']['completed']:
            comp = event['competitions'][0]['competitors']
            home = next(c for c in comp if c['homeAway'] == 'home')
            away = next(c for c in comp if c['homeAway'] == 'away')
            games.append({
                'home': home['team']['displayName'],
                'away': away['team']['displayName'],
                'home_score': int(home['score']),
                'away_score': int(away['score'])
            })
    return games

# Usage
nba = get_finished_games('basketball', 'nba', '20241126')
nhl = get_finished_games('hockey', 'nhl', '20241126')
epl = get_finished_games('soccer', 'eng.1', '20241123')
```

## Full Documentation

For complete research findings, alternative sources, and detailed comparisons, see:
- `SPORTS_SCRAPING_RESEARCH.md` - Full research report
- `sports_score_fetcher.py` - Ready-to-use implementation

## Important Notes

- ESPN's API is **unofficial** but widely used and stable
- No API key or authentication needed
- Free and likely to remain free
- For commercial use, consider legal implications
- Rate limiting is minimal but add delays to be respectful
- API structure may change (though it's been stable for years)

## Troubleshooting

**Getting 400 errors?**
- Make sure you're using HTTPS (not HTTP)
- Check date format is YYYYMMDD
- Don't use future dates

**No games returned?**
- Check if games were actually played that day
- NBA/NHL don't play every day
- Soccer leagues play mostly on weekends
- Use a recent past date you know had games

**Want more data?**
- The full API response includes much more (player stats, play-by-play, etc.)
- Check the full JSON response to see all available fields
- Example: `print(json.dumps(data, indent=2))`

## Success!

You should now be able to fetch finished sports scores reliably and for free. The ESPN API approach is clean, simple, and maintainable.

For any issues or questions, refer to the detailed research document.
