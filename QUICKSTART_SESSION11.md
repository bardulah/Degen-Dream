# Quick Start: Session 11 (API-Football + Discord Leaderboard)

**Last Updated**: Nov 27, 2025 | **Status**: ✅ Production Ready

## TL;DR - Complete Workflow

```bash
# 1. Set up environment
export OPENROUTER_API_KEY="sk-or-..."
export SENDER_EMAIL="your@gmail.com"
export SENDER_PASSWORD="app-password"
export CLI_USER_EMAIL="your@gmail.com"
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export RAPIDAPI_KEY="your-rapidapi-key"  # Optional, for real scores

# 2. Create bets
python main.py --games 5 --sample --no-live

# 3. Update results and post leaderboard
python main.py --update-results

# Done! Check Discord for leaderboard
```

---

## What This Does

### Phase 1: Create Bets (`--games 5`)
- Fetches today's games (sample data)
- 10 agents analyze each game
- Agents debate picks
- Oracle decides
- Bets placed and stored as PENDING

**Output:**
```
✅ BET PLACED: €89.64 on Barcelona
✅ BET PLACED: €42.17 on Lakers
...
💾 Stored in database for real result matching
```

### Phase 2: Match Results (`--update-results`)
- Fetches real match scores (or mock if unavailable)
- Matches bets with games using fuzzy matching
- Calculates outcomes (WON/LOST/PUSH)
- Updates agent leaderboard
- Posts to Discord

**Output:**
```
📊 Updating 2 pending bets...
✅ Oracle: Lakers → won (€+35.00)
❌ Oracle: Barcelona → lost (€-89.64)

🏆 LEADERBOARD (Last 7 Days)
🥇 Oracle | ROI: -18.83% | 3W-4L | 42.9% WR
✅ Leaderboard posted to Discord
```

---

## Configuration

### Required (All)
```bash
export OPENROUTER_API_KEY="your-openrouter-key"
export SENDER_EMAIL="your@gmail.com"
export SENDER_PASSWORD="app-password"
export CLI_USER_EMAIL="your@gmail.com"
```

### Optional (Recommended)
```bash
# For Discord leaderboard posting
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR-WEBHOOK-ID/YOUR-WEBHOOK-TOKEN"

# For real soccer scores (free tier, 100/day limit)
export RAPIDAPI_KEY="your-rapidapi-key"
```

### Optional (Advanced)
```bash
# Database (default: SQLite)
export DATABASE_URL="sqlite:///bratislava.db"
# Or PostgreSQL:
# export DATABASE_URL="postgresql://user:pass@localhost/degen"

# SMTP Server (default: Gmail)
export SMTP_SERVER="smtp.gmail.com"
```

---

## All Commands

```bash
# Create bets and email report
python main.py --games 5                    # Today's games
python main.py --games 5 --sample           # Sample games (no API)
python main.py --games 5 --daily --no-live  # Daily games, no Discord updates

# Update results and post leaderboard
python main.py --update-results

# View leaderboard
python main.py --leaderboard

# Show available leagues
python main.py --show-leagues

# Specify sport/league
python main.py --games 5 --sport soccer --leagues epl,la_liga
python main.py --games 5 --sports soccer,basketball
```

---

## Email Setup

### Gmail
1. Enable 2-factor authentication
2. Go to https://myaccount.google.com/apppasswords
3. Generate app password: `xxxx xxxx xxxx xxxx` (16 chars)
4. Set environment variables:
```bash
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="xxxx xxxx xxxx xxxx"
```

### Outlook
```bash
export SMTP_SERVER="smtp-mail.outlook.com"
export SENDER_EMAIL="your-email@outlook.com"
export SENDER_PASSWORD="your-app-password"
```

---

## Discord Setup

### Create Webhook
1. Go to your Discord server
2. Server Settings → Integrations → Webhooks
3. Click "New Webhook"
4. Copy webhook URL
5. Set environment variable:
```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/123456789/abcdefgh..."
```

### What Gets Posted
- **After `--games`**: Nothing (email only)
- **After `--update-results`**: Leaderboard embed with top 10 agents
  - Shows ROI, Win Rate, W-L record
  - Color: Gold (#FFD700)
  - Updated timestamp

---

## API-Football Setup (Optional)

### Get Free Key
1. Go to https://rapidapi.com/api-sports/api/api-football
2. Subscribe to free tier (100 req/day)
3. Copy API key from dashboard
4. Set environment variable:
```bash
export RAPIDAPI_KEY="your-api-key"
```

### Fallback Behavior
- If API key missing: Uses mock scores (for testing)
- If rate limit hit: Falls back to mock scores
- If API down: Uses mock scores
- **No bets are lost** - system always settles

---

## Workflow Examples

### Example 1: Daily Automated
```bash
# Morning: Create bets
python main.py --daily --games 10 --no-live

# Evening: Update results (after matches finish)
python main.py --update-results

# Discord shows leaderboard automatically
```

### Example 2: Development/Testing
```bash
# Test without APIs
python main.py --games 3 --sample --no-live

# Check results
python main.py --update-results

# View in console
python main.py --leaderboard
```

### Example 3: Specific Sport
```bash
# Only soccer bets
python main.py --games 5 --sport soccer

# Only EPL and La Liga
python main.py --games 5 --sport soccer --leagues epl,la_liga

# Update and post
python main.py --update-results
```

---

## Troubleshooting

### "Discord webhook not configured"
- Check `DISCORD_WEBHOOK_URL` is set: `echo $DISCORD_WEBHOOK_URL`
- Test webhook: `curl -X POST $DISCORD_WEBHOOK_URL -H "Content-Type: application/json" -d '{"content":"test"}'`

### "API-Football: API key missing"
- Set `RAPIDAPI_KEY` or use mock mode: `--sample`

### "Could not match: Team vs Team"
- System falls back to mock scores
- Fuzzy matching threshold: 60% (short names) or 75% (long names)
- Check team name normalization in results_matcher.py

### "Email not sending"
- For Gmail: Use app-specific password, not regular password
- For Outlook: Check SMTP_SERVER is correct
- Test: `python -c "from notification.email_sender import EmailSender; EmailSender().test()"`

### "Database locked"
- Close other connections to bratislava.db
- Delete `.db-journal` file if it exists
- Switch to PostgreSQL for concurrent access

---

## Database Schema

### Bets Table
- `id`: Unique bet ID
- `simulation_id`: Which simulation created this bet
- `agent_name`: Which agent placed it
- `bet_team`: Team bet on (e.g., "Lakers")
- `odds`: Decimal odds
- `stake`: Amount wagered
- `outcome`: PENDING, WON, LOST, PUSH
- `profit_loss`: P&L (null if pending)
- `created_at`: Timestamp
- `updated_at`: Settlement time

### Simulations Table
- `id`: Simulation ID
- `sport`: Sport type
- `num_games`: How many games analyzed
- `total_wagered`: Sum of all stakes
- `total_profit`: P&L across all bets
- `created_at`: Simulation timestamp

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Create 5 bets | 30-45s | LLM calls + Gemini Search |
| Fetch scores | 2-5s | API call or mock |
| Match 5 bets | < 1s | Fuzzy matching |
| Update database | < 100ms | Per bet |
| Post Discord | < 2s | Webhook call |
| **Total end-to-end** | **35-60s** | Includes all phases |

---

## What Happens to Old Bets?

- Bets stay in database indefinitely
- Leaderboard filters last 7 days by default: `--leaderboard`
- View older results: Check browser history or database directly
- Clear old bets: Backup database, then: `DELETE FROM bet WHERE created_at < DATE('now', '-30 days')`

---

## Next Features Coming

- ✅ API-Football (this session)
- ✅ Discord Leaderboard (this session)
- ⏳ Agent Learning (adjust confidence based on accuracy)
- ⏳ Scheduler (auto-run --daily at fixed time)
- ⏳ More Score APIs (Flashscore, ESPN)
- ⏳ Streamlit Dashboard
- ⏳ Docker Container

---

## File Locations

```
/home/matus/Projects/Degen-Dream/
├── main.py                          # Entry point
├── data/
│   ├── scores_fetcher.py           # API-Football integration
│   ├── results_matcher.py           # Fuzzy matching
│   ├── daily_odds_fetcher.py        # Fetch games
│   └── scrapers.py                  # Nike.sk scraper
├── database/
│   ├── schema.py                    # SQLAlchemy models
│   └── results_updater.py           # Settlement logic
├── agents/
│   ├── base_agent.py                # Base class
│   └── {sharp,insider,degen,bookie}_agent.py
├── notification/
│   ├── discord_notifier.py          # Discord posting
│   └── email_sender.py              # Email reports
├── simulation/
│   └── graph.py                     # Agent orchestration
└── bratislava.db                    # SQLite database
```

---

## Support

For issues, check:
1. AGENTS.md - Development progress
2. SESSION_11_SUMMARY.md - This session details
3. Console output - Detailed error messages
4. Database logs - Check `logs/` folder

---

**Ready?** Run:
```bash
python main.py --games 3 --sample --no-live && python main.py --update-results
```

Let me know if you hit any issues!
