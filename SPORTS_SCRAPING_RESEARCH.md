# Sports Score Scraping Research Report
## Best Methods for Fetching Finished Match Scores (Soccer, Basketball, Hockey)

**Date:** 2025-11-27
**Requirement:** Free, reliable, no clunky APIs

---

## Executive Summary

After thorough research, **ESPN's Hidden API is the clear winner** for fetching finished sports scores. It's technically not "scraping" but rather accessing undocumented JSON API endpoints that are free, reliable, and require no authentication.

### Top 3 Recommendations (Ranked):

1. **ESPN Hidden API** ⭐⭐⭐⭐⭐ (BEST OPTION)
2. **SofaScore Unofficial API** ⭐⭐⭐⭐
3. **FlashScore Web Scraping** ⭐⭐⭐

---

## 1. ESPN Hidden API (RECOMMENDED)

### Why This Is the Best Option:
- **No actual scraping needed** - JSON API endpoints
- **No authentication required** - Simple GET requests
- **Clean, structured data** - Properly formatted JSON responses
- **No anti-bot protection** on API endpoints
- **Covers all your sports**: NBA, NHL, Soccer (EPL, MLS, etc.)
- **Completely free** and reliable
- **Well-documented** by community (GitHub gists)

### Technical Details:

#### API Endpoints:

**Basketball (NBA):**
```
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard
```

**Hockey (NHL):**
```
https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard
```

**Soccer (various leagues):**
```
https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard
```

League codes:
- `eng.1` - English Premier League
- `usa.1` - MLS
- `esp.1` - La Liga
- `ger.1` - Bundesliga
- `ita.1` - Serie A
- `fra.1` - Ligue 1

#### Date Parameters:

Get finished games from a specific date:
```
?dates=20250115
```

Get games from a date range (max 13 months):
```
?dates=20250101-20250131
```

#### Response Structure:

The API returns JSON with:
- `events` array containing all games
- Each event has:
  - `id` - game ID
  - `name` - matchup description
  - `date` - game datetime
  - `status.type.completed` - boolean for finished games
  - `status.type.detail` - shows "Final" for finished games
  - `competitions[0].competitors` - home/away teams
  - `competitions[0].competitors[].score` - final scores

### Existing Python Libraries:

**1. espn_scraper** (most mature)
- GitHub: https://github.com/andr3w321/espn_scraper
- Supports: NFL, MLB, NBA, NCAAF, NCAAB, NCAAW, WNBA, NHL
- Handles scoreboards, boxscores, play-by-plays
- Optional caching

**2. Manual requests approach** (recommended for simplicity)
- Just use Python's `requests` library
- No dependencies beyond standard HTTP client

### Code Example:

```python
import requests
from datetime import datetime, timedelta

def get_finished_nba_games(date_str):
    """
    Get finished NBA games for a specific date.

    Args:
        date_str: Date in format 'YYYYMMDD' (e.g., '20250115')

    Returns:
        List of finished games with scores
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    params = {'dates': date_str}

    response = requests.get(url, params=params)
    data = response.json()

    finished_games = []

    for event in data.get('events', []):
        # Check if game is finished
        if event['status']['type']['completed']:
            game_info = {
                'game_id': event['id'],
                'date': event['date'],
                'status': event['status']['type']['detail'],  # "Final"
                'home_team': event['competitions'][0]['competitors'][0]['team']['displayName'],
                'away_team': event['competitions'][0]['competitors'][1]['team']['displayName'],
                'home_score': event['competitions'][0]['competitors'][0]['score'],
                'away_score': event['competitions'][0]['competitors'][1]['score']
            }
            finished_games.append(game_info)

    return finished_games

# Example usage:
games = get_finished_nba_games('20250115')
for game in games:
    print(f"{game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']} - {game['status']}")
```

```python
def get_finished_nhl_games(date_str):
    """Get finished NHL games for a specific date."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
    params = {'dates': date_str}

    response = requests.get(url, params=params)
    data = response.json()

    finished_games = []

    for event in data.get('events', []):
        if event['status']['type']['completed']:
            game_info = {
                'game_id': event['id'],
                'date': event['date'],
                'status': event['status']['type']['detail'],
                'home_team': event['competitions'][0]['competitors'][0]['team']['displayName'],
                'away_team': event['competitions'][0]['competitors'][1]['team']['displayName'],
                'home_score': event['competitions'][0]['competitors'][0]['score'],
                'away_score': event['competitions'][0]['competitors'][1]['score']
            }
            finished_games.append(game_info)

    return finished_games

def get_finished_soccer_games(league_code, date_str):
    """
    Get finished soccer games for a specific league and date.

    Args:
        league_code: League code (e.g., 'eng.1' for EPL, 'usa.1' for MLS)
        date_str: Date in format 'YYYYMMDD'
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
    params = {'dates': date_str}

    response = requests.get(url, params=params)
    data = response.json()

    finished_games = []

    for event in data.get('events', []):
        if event['status']['type']['completed']:
            game_info = {
                'game_id': event['id'],
                'date': event['date'],
                'status': event['status']['type']['detail'],
                'home_team': event['competitions'][0]['competitors'][0]['team']['displayName'],
                'away_team': event['competitions'][0]['competitors'][1]['team']['displayName'],
                'home_score': event['competitions'][0]['competitors'][0]['score'],
                'away_score': event['competitions'][0]['competitors'][1]['score']
            }
            finished_games.append(game_info)

    return finished_games

# Example: Get EPL games
epl_games = get_finished_soccer_games('eng.1', '20250115')
```

### Rate Limiting & Anti-Bot:
- **No strict rate limits observed** on API endpoints
- **No anti-bot protection** (it's an API, not a webpage)
- **Best practice**: Add 1-2 second delays between requests to be respectful
- No authentication or API keys required

### Terms of Service:
- **Unofficial API** - ESPN doesn't officially support this
- **Risk level**: Low for personal use, medium for commercial
- **Status**: Widely used by community, appears stable
- **Recommendation**: Fine for personal projects, be cautious with commercial use

### Pros:
✅ Easiest to implement (just HTTP GET requests)
✅ Clean JSON data structure
✅ No HTML parsing needed
✅ No anti-bot issues
✅ Covers all major sports
✅ Fast and reliable
✅ Free forever

### Cons:
❌ Unofficial (could theoretically be shut down)
❌ No official documentation (community-maintained)
❌ Terms of service gray area for commercial use

---

## 2. SofaScore Unofficial API

### Overview:
SofaScore has unofficial JSON API endpoints that can be accessed directly. Similar to ESPN but with more aggressive rate limiting.

### Technical Details:

#### API Endpoints:

**Live events:**
```
https://www.sofascore.com/api/v1/sport/{sport}/events/live
```

**Specific match data:**
```
https://www.sofascore.com/api/v1/event/{eventId}
```

**Tournament events:**
```
https://api.sofascore.com/api/v1/unique-tournament/{tournamentId}/season/{seasonId}/events/last/{page}
```

### Existing Python Libraries:

**sofascore-wrapper** (PyPI)
- Package: `pip install sofascore-wrapper`
- Provides Python API wrapper for SofaScore endpoints

**sofa-scrape** (GitHub)
- GitHub: https://github.com/donatogallo/sofa-scrape
- Command-line tool for scraping league data

### Code Example:

```python
import requests
import time

def get_sofascore_finished_matches(sport='football', tournament_id=17, season_id=52760):
    """
    Get finished matches from SofaScore.

    Args:
        sport: 'football', 'basketball', 'ice-hockey'
        tournament_id: Tournament ID (e.g., 17 for Premier League)
        season_id: Season ID
    """
    url = f"https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/last/0"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    finished_matches = []

    for event in data.get('events', []):
        if event['status']['type'] == 'finished':
            match_info = {
                'id': event['id'],
                'home_team': event['homeTeam']['name'],
                'away_team': event['awayTeam']['name'],
                'home_score': event['homeScore']['current'],
                'away_score': event['awayScore']['current'],
                'status': event['status']['description']
            }
            finished_matches.append(match_info)

    return finished_matches

# IMPORTANT: Add delay between requests!
time.sleep(30)  # SofaScore requires 25-30 seconds between calls
```

### Rate Limiting & Anti-Bot:
- **STRICT rate limiting**: Must wait 25-30 seconds between requests
- **Cloudflare protection**: May get 403/503 errors if you exceed limits
- **IP bans possible** after ~500-1500 requests without proper throttling
- **Recommendation**: Use proxy rotation for large-scale scraping

### Terms of Service:
- **Unofficial API access**
- **Risk level**: Medium - aggressive anti-bot measures
- **Better for**: Small-scale, infrequent requests

### Pros:
✅ Good data quality
✅ Comprehensive sports coverage
✅ JSON API (no HTML parsing)

### Cons:
❌ Strict rate limiting (25-30 sec between requests)
❌ Cloudflare protection
❌ IP bans possible
❌ Less reliable than ESPN for high-volume requests

---

## 3. FlashScore Web Scraping

### Overview:
FlashScore requires actual web scraping (not API access). More complex but has very comprehensive data.

### Technical Details:

FlashScore uses JavaScript to render content, so you need:
- **Selenium** or **Playwright** for browser automation
- **BeautifulSoup** for HTML parsing
- More complex setup than API approaches

### Existing Python Libraries:

**flashscore-python** (GitHub)
- GitHub: https://github.com/carlzoo/flashscore-python
- Most mature FlashScore library

**Flashscore-scraper** (GitHub)
- GitHub: https://github.com/tadeq/Flashscore-scraper
- Gathers historical data for football leagues
- Uses Firefox/Chrome with Selenium

**flashscore-scraper** (PyPI)
- Package available on PyPI
- Includes built-in rate limit protection

### Code Example:

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def scrape_flashscore_finished_matches(sport='football', league_url=''):
    """
    Scrape finished matches from FlashScore using Selenium.

    Args:
        sport: 'football', 'basketball', 'hockey'
        league_url: Full FlashScore URL for the league
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(league_url)
        time.sleep(3)  # Wait for JavaScript to load

        # Wait for matches to load
        wait = WebDriverWait(driver, 10)
        matches = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "event__match"))
        )

        finished_matches = []

        for match in matches:
            # Extract match data from HTML elements
            home_team = match.find_element(By.CLASS_NAME, "event__participant--home").text
            away_team = match.find_element(By.CLASS_NAME, "event__participant--away").text
            score = match.find_element(By.CLASS_NAME, "event__score").text

            finished_matches.append({
                'home_team': home_team,
                'away_team': away_team,
                'score': score
            })

        return finished_matches

    finally:
        driver.quit()
```

### Rate Limiting & Anti-Bot:
- **Moderate anti-bot protection**
- **JavaScript rendering required** (must use Selenium/Playwright)
- **Rate limiting exists** but less strict than SofaScore
- **Best practice**: Rotate user agents, add random delays

### Terms of Service:
- **Web scraping ToS concerns** - check robots.txt
- **Risk level**: Medium for scraping
- **Cloudflare may block aggressive scraping**

### Pros:
✅ Very comprehensive data
✅ Covers many sports and leagues
✅ Good existing libraries
✅ Real-time and historical data

### Cons:
❌ Requires Selenium (browser automation)
❌ More complex setup
❌ Slower than API approaches
❌ Anti-bot protection
❌ JavaScript dependency

---

## 4. TheScore.com

### Overview:
Less documentation available compared to other sources. Not recommended as primary option.

### Status:
- Limited Python libraries found
- Older tutorials (2019) available
- Better alternatives exist (ESPN, SofaScore)

### Recommendation:
**Skip this source** - ESPN and SofaScore are better options.

---

## 5. Google Sports

### Overview:
Google doesn't offer official sports API. Access requires:
- Third-party scraping services (SerpApi, ScrapingBee) - **PAID**
- Direct scraping of Google search results - **ToS violations**

### Recommendation:
**Not recommended** - Against Google ToS and requires paid services.

---

## Final Recommendation

### For Your Use Case (Finished Match Scores):

**PRIMARY:** Use **ESPN Hidden API**

**Reasons:**
1. Simplest implementation (just HTTP GET)
2. No anti-bot issues
3. Clean JSON data
4. Covers all your sports (NBA, NHL, Soccer)
5. Fast and reliable
6. Completely free
7. No authentication needed

**BACKUP:** Use **SofaScore API** for additional data or as fallback

**Implementation Strategy:**

```python
import requests
from datetime import datetime, timedelta
import time

class SportsScoreFetcher:
    """Unified sports score fetcher using ESPN API."""

    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _get_scoreboard(self, sport, league, date_str):
        """Generic scoreboard fetcher."""
        url = f"{self.BASE_URL}/{sport}/{league}/scoreboard"
        params = {'dates': date_str}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_nba_scores(self, date_str):
        """Get NBA finished games."""
        data = self._get_scoreboard('basketball', 'nba', date_str)
        return self._parse_finished_games(data)

    def get_nhl_scores(self, date_str):
        """Get NHL finished games."""
        data = self._get_scoreboard('hockey', 'nhl', date_str)
        return self._parse_finished_games(data)

    def get_soccer_scores(self, league_code, date_str):
        """
        Get soccer finished games.

        League codes:
        - eng.1: Premier League
        - usa.1: MLS
        - esp.1: La Liga
        - ger.1: Bundesliga
        - ita.1: Serie A
        - fra.1: Ligue 1
        """
        data = self._get_scoreboard('soccer', league_code, date_str)
        return self._parse_finished_games(data)

    def _parse_finished_games(self, data):
        """Parse finished games from ESPN API response."""
        finished_games = []

        for event in data.get('events', []):
            if not event['status']['type']['completed']:
                continue

            competition = event['competitions'][0]
            competitors = competition['competitors']

            # Find home and away teams
            home = next(c for c in competitors if c['homeAway'] == 'home')
            away = next(c for c in competitors if c['homeAway'] == 'away')

            game_info = {
                'game_id': event['id'],
                'date': event['date'],
                'status': event['status']['type']['detail'],
                'home_team': home['team']['displayName'],
                'away_team': away['team']['displayName'],
                'home_score': int(home['score']),
                'away_score': int(away['score']),
                'winner': home['team']['displayName'] if int(home['score']) > int(away['score']) else away['team']['displayName']
            }
            finished_games.append(game_info)

        return finished_games

# Usage example:
if __name__ == '__main__':
    fetcher = SportsScoreFetcher()

    # Get yesterday's date
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

    # Fetch NBA scores
    print("NBA Games:")
    nba_games = fetcher.get_nba_scores(yesterday)
    for game in nba_games:
        print(f"  {game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']} - {game['status']}")

    time.sleep(1)  # Be respectful

    # Fetch NHL scores
    print("\nNHL Games:")
    nhl_games = fetcher.get_nhl_scores(yesterday)
    for game in nhl_games:
        print(f"  {game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']} - {game['status']}")

    time.sleep(1)

    # Fetch Premier League scores
    print("\nPremier League Games:")
    epl_games = fetcher.get_soccer_scores('eng.1', yesterday)
    for game in epl_games:
        print(f"  {game['away_team']} {game['away_score']} @ {game['home_team']} {game['home_score']} - {game['status']}")
```

### Best Practices:

1. **Add delays**: 1-2 seconds between requests
2. **Handle errors gracefully**: Network issues, missing data
3. **Cache results**: Save API responses to avoid repeated calls
4. **Use date ranges**: Batch requests when possible
5. **Monitor for changes**: ESPN may update API structure

### Risk Mitigation:

- **Primary**: ESPN API (lowest risk)
- **Backup**: SofaScore API (with rate limiting)
- **Emergency**: FlashScore scraping (most complex)

---

## Sources & References

### ESPN API:
- [ESPN Hidden API Docs (GitHub Gist)](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b)
- [ESPN Scraper Library](https://github.com/andr3w321/espn_scraper)
- [ESPN API Guide - Zuplo](https://zuplo.com/learning-center/espn-hidden-api-guide)
- [Public ESPN API Docs](https://github.com/pseudo-r/Public-ESPN-API)

### SofaScore:
- [SofaScore Wrapper (PyPI)](https://pypi.org/project/sofascore-wrapper/)
- [Stack Overflow: Scraping SofaScore](https://stackoverflow.com/questions/59024776/how-to-scrape-football-results-from-sofascore-using-python)
- [ScraperFC Documentation](https://scraperfc.readthedocs.io/en/latest/sofascore.html)

### FlashScore:
- [FlashScore Python Library](https://github.com/carlzoo/flashscore-python)
- [FlashScore Scraper](https://github.com/tadeq/Flashscore-scraper)

### General:
- [PySport Open Source Overview](https://opensource.pysport.org/)
- [Sports Data Scraping Guide](https://datamam.com/sports-websites-scraping/)

---

## Conclusion

**ESPN's Hidden API is your best bet.** It's free, reliable, easy to implement, and covers all your required sports. Start with the provided code examples and you'll have finished match scores in minutes, not hours.

If ESPN ever shuts down their API (unlikely but possible), fall back to SofaScore with proper rate limiting, or implement FlashScore scraping as a last resort.
