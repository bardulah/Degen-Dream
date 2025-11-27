# Bratislava Betting Syndicate - Command Reference

## Quick Start (Recommended)

```bash
# Run a simulation with today's top games
python main.py --daily --games 5 --no-live

# Check agent leaderboard
python main.py --leaderboard

# Use sample data (no API calls)
python main.py --games 3 --sample --no-live
```

## All CLI Commands

### Main Simulation Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `--games N` | Number of games to analyze | `--games 10` |
| `--sport SPORT` | Sport to analyze | `--sport soccer` |
| `--daily` | Use today's top leagues (default multi-sport) | `--daily --games 5` |
| `--sample` | Use sample data (no API calls) | `--sample` |
| `--aggregator` | Use multi-source odds aggregator | `--aggregator` |
| `--no-live` | Disable live console output | `--no-live` |

### Advanced Options

| Command | Purpose | Example |
|---------|---------|---------|
| `--sports LIST` | Specific sports (comma-separated) | `--sports soccer,basketball` |
| `--leagues LIST` | Specific leagues (comma-separated) | `--leagues epl,nba` |
| `--max-per-sport N` | Max games per sport | `--max-per-sport 3` |
| `--show-leagues` | Show available leagues and exit | `--show-leagues` |

### New Analysis Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `--leaderboard` | Show agent performance stats | `--leaderboard` |
| `--update-results` | Update pending bets with results | `--update-results` (experimental) |

## Common Usage Patterns

### Pattern 1: Daily Report
```bash
# Analyze today's top matches, send email/Discord
python main.py --daily --games 10
```

### Pattern 2: Sample Testing (No APIs)
```bash
# Quick test with sample data
python main.py --games 3 --sample --no-live
```

### Pattern 3: Specific Sport
```bash
# Only analyze Premier League matches
python main.py --sport soccer --leagues epl --games 5 --daily
```

### Pattern 4: Check Performance
```bash
# See how agents are doing
python main.py --leaderboard
```

### Pattern 5: Multi-Sport Analysis
```bash
# Analyze soccer, basketball, hockey
python main.py --sports soccer,basketball,hockey --games 5 --daily
```

### Pattern 6: Development (Silent Mode)
```bash
# No console output, just database + email + Discord
python main.py --daily --games 5 --no-live
```

## Environment Setup

```bash
# Set API keys
export OPENROUTER_API_KEY="your-key"
export ODDS_API_KEY="your-key"
export DISCORD_WEBHOOK_URL="your-webhook"
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="app-password"
export CLI_USER_EMAIL="your-email@gmail.com"

# Set database (optional, default is SQLite)
export DATABASE_URL="sqlite:///bratislava.db"
# or for PostgreSQL:
# export DATABASE_URL="postgresql://user:pass@localhost/degen_dream"
```

## Output Files

### Database
- `bratislava.db` - SQLite database (all bets, simulations, agents)

### Logs
- `logs/` - Structured logging
- Console - Real-time agent analysis (if not `--no-live`)

### Email
- HTML reports sent to `CLI_USER_EMAIL`
- Section: Oracle's Choice, Vote Breakdown, All Picks

### Discord
- Live agent picks (one per line)
- Debate messages
- Final decision with vote counts
- Parlay summaries

## Configuration Files

### `.env` (Create for custom settings)
```
OPENROUTER_API_KEY=sk-or-...
ODDS_API_KEY=...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SENDER_EMAIL=your@gmail.com
SENDER_PASSWORD=app-specific-password
CLI_USER_EMAIL=your@gmail.com
DATABASE_URL=sqlite:///bratislava.db
LOG_LEVEL=INFO
```

### `.streamlit/config.toml` (Already configured)
- Caching enabled
- Dark theme
- Performance optimizations

## Troubleshooting

### "No games found"
```bash
# Try with --sample
python main.py --games 5 --sample

# Or specify a sport
python main.py --daily --sport soccer --games 5
```

### "Email not sending"
```bash
# Check credentials
echo $SENDER_EMAIL
echo $SENDER_PASSWORD  # Should be app-specific password for Gmail

# Gmail: 2FA must be enabled, use app-specific password from:
# https://myaccount.google.com/apppasswords
```

### "Discord not notifying"
```bash
# Test webhook (check rate limits)
curl -X POST $DISCORD_WEBHOOK_URL -d '{"content":"test"}' \
  -H "Content-Type: application/json"

# 429 errors are normal (rate limited) and non-blocking
```

### "API rate limited (429)"
```bash
# OddsAPI has rate limits based on plan
# Nike.sk scraper is reliable fallback
# System will retry automatically with backoff
```

### "Database locked"
```bash
# Close other processes
rm -f bratislava.db-journal

# Or use PostgreSQL for concurrent access
export DATABASE_URL="postgresql://user:pass@localhost/degen_dream"
```

## Performance Tips

1. **Use `--sample` for testing**
   - Fastest, no API calls
   - Perfect for development

2. **Use `--daily --no-live` for production**
   - Fetches real odds
   - No console output (faster)
   - Still sends email/Discord

3. **Limit games with `--max-per-sport`**
   - Less LLM calls
   - Faster execution
   - Still gets good coverage

4. **Cache leagues**
   - System caches odds for 30 minutes
   - Run multiple sims in that window
   - Saves API calls

## Advanced: Running Multiple Simulations

```bash
# Simulation 1: European soccer
python main.py --sports soccer --leagues epl,la_liga,bundesliga --games 5 --no-live &

# Simulation 2: Basketball + Hockey
python main.py --sports basketball,hockey --games 5 --no-live &

# Wait for both
wait

# Check results
python main.py --leaderboard
```

## Integration Examples

### Cron Job (Daily Analysis)
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 PM)
0 14 * * * cd /path/to/degen-dream && python main.py --daily --games 10 --no-live
```

### Discord Bot
```python
# See notification/discord_notifier.py
# Already integrated via DISCORD_WEBHOOK_URL
```

### Email Reports
```python
# See notification/email_sender.py
# Configured via SENDER_EMAIL/SENDER_PASSWORD/CLI_USER_EMAIL
```

## Reference: Agent Types

| Agent | Type | Style | Confidence |
|-------|------|-------|------------|
| Viktor | Sharp | Data-driven, EV focused | Cautious |
| Elena | Sharp | Line movement, closing odds | Moderate |
| Boris | Sharp | Arbitrage opportunities | Cautious |
| Nikolai | Insider | Leaked info, sources | High |
| Petra | Insider | Training ground intel | High |
| Jozef | Degen | Large parlays, YOLO | Very High |
| Marian | Degen | Superstitions, vibes | Very High |
| Lucia | Degen | Simple rules, home teams | Very High |
| Tomáš | Bookie | Trap squares, juice | Moderate |
| Katarína | Bookie | Balance books, inefficiency | Moderate |

## Reference: Available Sports

```bash
python main.py --show-leagues
```

Returns:
- Soccer: EPL, La Liga, Bundesliga, Serie A, Ligue 1, Champions League, etc.
- Basketball: NBA, Euroleague
- Hockey: NHL
- Tennis: ATP, WTA

---

**Last Updated**: Session 9 (Nov 27, 2025)
**Status**: ✅ Complete and working
