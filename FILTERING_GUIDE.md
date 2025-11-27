# Game Filtering Guide

Easily select which sports, leagues, and number of games to analyze.

## Quick Start

### Show all available leagues
```bash
python main.py --daily --show-leagues
```

Output:
```
SOCCER:
  • premier_league
  • la_liga
  • ligue_1
  • ...

BASKETBALL:
  • nba
  • euroleague
  • ...
```

## Filter Options

### By Sport
Only analyze soccer and basketball:
```bash
python main.py --daily --games 5 --sports soccer,basketball
```

### By League
Only analyze Premier League games:
```bash
python main.py --daily --games 5 --leagues premier_league
```

Multiple leagues:
```bash
python main.py --daily --games 5 --leagues premier_league,la_liga,nba
```

### By Count Per Sport
Maximum 3 games per sport:
```bash
python main.py --daily --games 10 --max-per-sport 3
```

(Gets 3 soccer + 3 basketball + 3 hockey, etc., up to 10 total)

## Combined Examples

### Example 1: Top 5 European Leagues
```bash
python main.py --daily --games 10 \
  --sports soccer \
  --leagues premier_league,la_liga,ligue_1,bundesliga,serie_a \
  --max-per-sport 5
```

### Example 2: Basketball Only (NBA)
```bash
python main.py --daily --games 5 \
  --sports basketball \
  --leagues nba
```

### Example 3: Multi-sport Balance (2 per sport)
```bash
python main.py --daily --games 10 \
  --sports soccer,basketball,hockey \
  --max-per-sport 2
```

### Example 4: All Unknown Leagues (good for edge cases)
```bash
python main.py --daily --games 5 \
  --leagues unknown_soccer,unknown_basketball
```

## Available Leagues

Nike.sk scraper infers leagues from team names. Here's the current mapping:

### Soccer
- `premier_league` - Arsenal, Liverpool, Chelsea, Manchester, Tottenham
- `la_liga` - Real Madrid, Barcelona, Atletico Madrid
- `bundesliga` - Bayern, Dortmund, Borussia
- `serie_a` - Juventus, AC Milan, Inter, Napoli
- `ligue_1` - Paris, Lyon
- `eredivisie` - Ajax, PSV
- `slovakia` - Slovan, Dunajska, Zilina
- `unknown_soccer` - Teams not in mapping

### Basketball
- `nba` - Lakers, Warriors, Celtics, Heat, Suns, Denver
- `euroleague` - Monaco, Real Madrid, Panathinaikos, Olympiakos, Efes
- `unknown_basketball` - Teams not in mapping

### Hockey
- `shl` - Zurich, Zug, Servette
- `slovakia` - Banská, Nitra
- `unknown_hockey` - Teams not in mapping

### Tennis/Other
- `unknown_[sport]` - Most tennis and other sports don't have league mappings yet

## How League Inference Works

1. Team names are checked against `TEAM_LEAGUE_MAP` in `NikeScraper`
2. If either home or away team matches a known team, game gets that league
3. If no match, game gets `unknown_[sport]` as default
4. You can easily extend the mapping by editing `TEAM_LEAGUE_MAP` in `data/scrapers.py`

## Expand League Mapping

Edit `data/scrapers.py` and add teams to `TEAM_LEAGUE_MAP`:

```python
TEAM_LEAGUE_MAP = {
    # Your new teams
    "manchester united": "premier_league",
    "sevilla": "la_liga",
    "juventus": "serie_a",
    # ... etc
}
```

Then re-run with `--show-leagues` to verify.

## How Filtering Works

1. **Nike.sk scrapes all sports** (343 games/day)
2. **Get available leagues** - scans all games to find leagues
3. **Apply filters** in order:
   - Sport filter (keep only selected sports)
   - League filter (keep only selected leagues)
   - Count limit (keep max N per sport)
4. **Agents analyze** filtered games

## Database

All games are stored in database with league info:
```sql
SELECT sport, league, COUNT(*) as count 
FROM bets 
GROUP BY sport, league
ORDER BY count DESC;
```

## Tips

- Use `--show-leagues` first to see what's available
- Start with `--max-per-sport 1` to test filters
- Combine `--sports` + `--leagues` for fine control
- Use `--games 100` to ensure enough games after filtering
- Unknown leagues are great for testing edge cases

