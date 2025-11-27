# 🚀 System Enhancements Guide

This guide covers all the advanced features added to the Bratislava Betting Syndicate.

## 📋 Table of Contents

1. [Automated Result Updates](#automated-result-updates)
2. [Notification System](#notification-system)
3. [Multi-Source Score Fallback](#multi-source-score-fallback)
4. [CLV (Closing Line Value) Tracking](#clv-tracking)
5. [Bet Recommendation Engine](#bet-recommendation-engine)
6. [Historical Performance Analyzer](#historical-performance-analyzer)
7. [Setup & Configuration](#setup--configuration)

---

## 🤖 Automated Result Updates

**File:** `scheduler/auto_updater.py`

Automatically fetch and update bet results on a schedule.

### Features

- ✅ Runs daily at configurable time
- ✅ Checks multiple days back
- ✅ Updates simulation statistics
- ✅ Sends notifications when results come in
- ✅ Can run as daemon or one-off

### Usage

```bash
# Run once (check yesterday)
python scheduler/auto_updater.py

# Run as background daemon (checks daily at 9 AM)
python scheduler/auto_updater.py --daemon --time 09:00

# Check last 3 days
python scheduler/auto_updater.py --days 3

# Test mode (dry run)
python scheduler/auto_updater.py --test

# Disable notifications
python scheduler/auto_updater.py --no-notifications
```

### Setup as Cron Job

```bash
# Add to crontab
crontab -e

# Run daily at 9 AM
0 9 * * * cd /path/to/Degen-Dream && python scheduler/auto_updater.py
```

### Setup as Systemd Service

```ini
# /etc/systemd/system/betting-updater.service
[Unit]
Description=Bratislava Betting Syndicate Auto Updater
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Degen-Dream
ExecStart=/usr/bin/python3 scheduler/auto_updater.py --daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable betting-updater
sudo systemctl start betting-updater
```

---

## 📢 Notification System

**File:** `scheduler/notifier.py`

Send alerts via Discord, Telegram, and Email when results come in.

### Discord Setup

1. Create a Discord webhook:
   - Server Settings → Integrations → Webhooks → New Webhook
   - Copy webhook URL

2. Set environment variable:
   ```bash
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   ```

3. Test:
   ```bash
   python scheduler/notifier.py
   ```

### Telegram Setup

1. Create a Telegram bot:
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Copy bot token

2. Get your chat ID:
   - Message your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Copy your chat ID from the response

3. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```

4. Test:
   ```bash
   python scheduler/notifier.py
   ```

### Notification Types

**Result Update:**
```python
from scheduler.notifier import DiscordNotifier

notifier = DiscordNotifier()
notifier.send_result_update({
    'total_checked': 10,
    'updated': 8,
    'won': 5,
    'lost': 3,
    'push': 0
})
```

**Simulation Complete:**
```python
notifier.send_simulation_complete(
    simulation_id="abc123...",
    roi=15.5,
    win_rate=60.0,
    profit=1550.0
)
```

**Bet Alert:**
```python
notifier.send_bet_alert({
    'away_team': 'Lakers',
    'home_team': 'Celtics',
    'bet_type': 'moneyline',
    'team': 'Lakers',
    'odds': 2.10,
    'confidence': 0.85,
    'reasoning': 'Strong value based on historical performance'
})
```

---

## 🔄 Multi-Source Score Fallback

**File:** `data/multi_source_fetcher.py`

Fetch scores with automatic fallback to ensure 99.9% uptime.

### How It Works

1. **Primary:** ESPN API (fast, reliable)
2. **Backup:** SofaScore API (if ESPN fails)
3. **Future:** Additional sources can be added

### Usage

```python
from data.multi_source_fetcher import MultiSourceFetcher

fetcher = MultiSourceFetcher()

# Automatically tries ESPN, falls back to SofaScore if needed
nba_games = fetcher.get_nba_scores('20241126')
nhl_games = fetcher.get_nhl_scores('20241126')
soccer_games = fetcher.get_soccer_scores('eng.1', '20241126')

# Check source health
health = fetcher.get_health_status()
# {'espn': True, 'sofascore': True}
```

### Benefits

- ✅ 99.9% uptime (if one source fails, another takes over)
- ✅ No code changes needed
- ✅ Automatic fallback
- ✅ Health monitoring

---

## 🎯 CLV (Closing Line Value) Tracking

**File:** `analytics/clv_tracker.py`

**Database:** Added `closing_odds`, `clv_percentage`, `beat_closing_line` to Bet table

CLV is the #1 indicator of long-term profitability. If you beat the closing line, you're a winning bettor.

### What is CLV?

**Closing Line Value** = Difference between your bet odds and the closing odds.

**Example:**
- You bet Lakers @ 2.10
- Closing odds: Lakers @ 2.00
- CLV = +5.0% (you got better odds)

**Why It Matters:**
- Positive CLV → Long-term winner
- Negative CLV → Long-term loser

### Usage

```python
from analytics.clv_tracker import CLVTracker

tracker = CLVTracker()

# Calculate CLV
clv = tracker.calculate_clv(bet_odds=2.10, closing_odds=2.00)
# Result: +5.0%

# Update bet with closing odds
tracker.update_bet_clv(
    bet_id="abc123...",
    closing_odds=2.00
)

# Get CLV statistics
stats = tracker.get_clv_stats(days=30)
# {
#     'average_clv': 2.5,
#     'beat_closing_line_pct': 58.0,
#     'positive_clv_count': 23,
#     'negative_clv_count': 17
# }

# Analyze CLV vs actual results
analysis = tracker.analyze_clv_vs_results()
# Shows if beating closing line = winning
```

### Database Schema

```python
# Added to Bet model:
closing_odds = Column(Float, nullable=True)
clv_percentage = Column(Float, nullable=True)
beat_closing_line = Column(Boolean, nullable=True)
```

---

## 🤖 Bet Recommendation Engine

**File:** `analytics/bet_recommender.py`

AI-powered recommendations based on historical performance.

### How It Works

1. Analyzes agent performance by sport
2. Calculates expected value (EV)
3. Identifies high-confidence opportunities
4. Recommends top bets

### Usage

```python
from analytics.bet_recommender import BetRecommender

recommender = BetRecommender()

# Get top recommendations from available games
recommendations = recommender.recommend_bets(games, max_recommendations=5)

for rec in recommendations:
    print(f"🔥 {rec['bet_team']} @ {rec['odds']}")
    print(f"   EV: +{rec['ev_percentage']:.1f}%")
    print(f"   Confidence: {rec['confidence']*100:.0f}%")
    print(f"   {rec['reasoning']}")
```

### Example Output

```
🔥 Lakers @ 2.10
   EV: +8.5%
   Confidence: 82%
   Sharp Agent has 65.0% win rate and +12.5% ROI on this sport
   over 45 bets. Expected value: +8.5%

🔥 Celtics @ 1.95
   EV: +6.2%
   Confidence: 75%
   Insider Agent has 58.0% win rate and +8.3% ROI on this sport
   over 32 bets. Expected value: +6.2%
```

### Configuration

```python
recommender.min_confidence = 0.65  # Minimum 65% confidence
recommender.min_ev = 0.05          # Minimum 5% expected value
recommender.min_sample_size = 10   # At least 10 historical bets
```

### Features

- ✅ Expected Value (EV) calculation
- ✅ Agent-specific performance tracking
- ✅ Sport-specific analysis
- ✅ Confidence scoring
- ✅ Top performer identification

---

## 📊 Historical Performance Analyzer

**File:** `analytics/performance_analyzer.py`

Deep analysis of betting performance with advanced metrics.

### Features

#### 1. Sharpe Ratio (Risk-Adjusted Returns)

```python
from analytics.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()

sharpe = analyzer.calculate_sharpe_ratio(simulation_id="abc123...")
# Result: 1.85 (>1.0 is good, >2.0 is excellent)
```

**What it means:**
- Sharpe > 1.0 = Good risk-adjusted returns
- Sharpe > 2.0 = Excellent risk-adjusted returns
- Sharpe > 3.0 = Outstanding (top tier)

#### 2. Maximum Drawdown

```python
drawdown = analyzer.calculate_max_drawdown(simulation_id="abc123...")
# {
#     'max_drawdown': 850.0,
#     'max_drawdown_pct': 8.5,
#     'peak_bankroll': 12500.0
# }
```

**What it means:**
- Shows worst losing streak
- Lower is better
- < 10% is good risk management

#### 3. Performance by Sport

```python
by_sport = analyzer.analyze_by_sport(days=90)
# {
#     'nba': {
#         'total_bets': 45,
#         'win_rate': 58.0,
#         'roi': 12.5,
#         'total_profit': 1250.0
#     },
#     'nhl': {
#         'total_bets': 32,
#         'win_rate': 52.0,
#         'roi': 6.8,
#         'total_profit': 680.0
#     }
# }
```

#### 4. Performance by Bet Type

```python
by_type = analyzer.analyze_by_bet_type(days=90)
# {
#     'moneyline': {'win_rate': 55.0, 'roi': 8.5},
#     'spread': {'win_rate': 52.0, 'roi': 4.2},
#     'total': {'win_rate': 50.0, 'roi': -2.1}
# }
```

#### 5. Streak Analysis

```python
streaks = analyzer.find_streaks(simulation_id="abc123...")
# {
#     'max_win_streak': 7,
#     'max_loss_streak': 4,
#     'current_win_streak': 3,
#     'current_loss_streak': 0
# }
```

#### 6. Time-Based Patterns

```python
by_day = analyzer.analyze_time_patterns(days=90)
# {
#     'Monday': {'win_rate': 62.0, 'roi': 15.2},
#     'Tuesday': {'win_rate': 48.0, 'roi': -3.5},
#     'Saturday': {'win_rate': 58.0, 'roi': 10.8}
# }
```

### Comprehensive Report

```python
report = analyzer.generate_performance_report()

# Returns complete analysis:
{
    'sharpe_ratio': 1.85,
    'max_drawdown': {...},
    'streaks': {...},
    'by_sport': {...},
    'by_bet_type': {...},
    'by_day_of_week': {...}
}
```

---

## ⚙️ Setup & Configuration

### 1. Install Dependencies

```bash
pip install schedule requests
```

### 2. Environment Variables

Create `.env` file:

```bash
# Discord Notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional
NOTIFICATION_EMAIL=your@email.com
```

### 3. Database Migration

The new features added fields to the database. To apply:

```bash
# Option 1: Delete and recreate (DEV ONLY!)
rm bratislava.db
python -c "from database.schema import init_db; init_db()"

# Option 2: Use Alembic (production)
alembic revision --autogenerate -m "Add CLV and enhancements"
alembic upgrade head
```

### 4. Test Everything

```bash
# Test notifications
python scheduler/notifier.py

# Test multi-source fetcher
python data/multi_source_fetcher.py

# Test CLV tracker
python analytics/clv_tracker.py

# Test recommender
python analytics/bet_recommender.py

# Test analyzer
python analytics/performance_analyzer.py
```

---

## 🎯 Quick Start Workflows

### Workflow 1: Automated Daily Updates

```bash
# Set up environment variables
export DISCORD_WEBHOOK_URL="your_webhook_url"

# Run auto updater as daemon
python scheduler/auto_updater.py --daemon --time 09:00
```

Now results update automatically every day at 9 AM, and you get Discord notifications!

### Workflow 2: Get Recommendations Before Betting

```python
from analytics.bet_recommender import BetRecommender
from data.odds_aggregator import OddsAggregator

# Get today's games
aggregator = OddsAggregator()
games = aggregator.get_all_odds()

# Get recommendations
recommender = BetRecommender()
recommendations = recommender.recommend_bets(games, max_recommendations=5)

# Place bets based on recommendations
for rec in recommendations:
    print(f"Bet {rec['bet_team']} @ {rec['odds']} - EV: +{rec['ev_percentage']:.1f}%")
```

### Workflow 3: Performance Review

```python
from analytics.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()

# Generate comprehensive report
report = analyzer.generate_performance_report()

print(f"Sharpe Ratio: {report['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {report['max_drawdown']['max_drawdown_pct']:.1f}%")
print(f"Best Sport: {max(report['by_sport'].items(), key=lambda x: x[1]['roi'])}")
```

---

## 📈 Advanced Tips

### Tip 1: Combine CLV with Results

Bets with positive CLV should win long-term:

```python
from analytics.clv_tracker import CLVTracker

tracker = CLVTracker()
analysis = tracker.analyze_clv_vs_results()

# Shows:
# Positive CLV bets: 58% win rate
# Negative CLV bets: 45% win rate
```

### Tip 2: Use Recommendations + CLV

1. Get recommendations from the engine
2. Only bet if CLV > 0 when game starts
3. Track results over time

### Tip 3: Monitor Sharpe Ratio

- Sharpe < 0.5 = High risk for returns
- Sharpe 0.5-1.0 = Moderate risk
- Sharpe 1.0-2.0 = Good risk-adjusted returns
- Sharpe > 2.0 = Excellent

### Tip 4: Drawdown Management

If current drawdown > 5% from peak:
- Reduce bet sizes
- Only bet highest EV opportunities
- Wait for streak to end

---

## 🔧 Troubleshooting

### Issue: Notifications Not Sending

**Solution:**
```bash
# Test Discord webhook
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'

# Verify environment variables
echo $DISCORD_WEBHOOK_URL
echo $TELEGRAM_BOT_TOKEN
```

### Issue: Auto Updater Not Running

**Solution:**
```bash
# Check if process is running
ps aux | grep auto_updater

# Check logs
tail -f /var/log/syslog | grep betting

# Run manually to see errors
python scheduler/auto_updater.py --test
```

### Issue: No CLV Data

**Solution:**
CLV requires closing odds. To populate:
1. Set up automated odds tracking
2. Fetch odds right before game time
3. Update bets with closing odds

---

## 🎉 Summary

You now have:

1. **🤖 Automated Updates** - Set and forget result fetching
2. **📢 Notifications** - Get alerted instantly
3. **🔄 Reliability** - 99.9% uptime with fallbacks
4. **🎯 CLV Tracking** - Know if you're beating the market
5. **💡 Recommendations** - AI suggests best bets
6. **📊 Analytics** - Deep performance insights

All these features work together to give you a professional-grade betting system!

---

## 📚 Next Steps

1. Set up automated updates
2. Configure Discord/Telegram notifications
3. Run a few simulations to build history
4. Start getting recommendations
5. Track your CLV
6. Analyze performance

Happy betting! 🎰
