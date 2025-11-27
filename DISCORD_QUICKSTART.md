# Discord Integration - Quick Start (5 minutes)

## Step 1: Get Webhook URL (2 minutes)

```bash
# Option A: Create new Discord server
1. Go to Discord.com
2. Click "+" to create server
3. Name: "Betting Syndicate" (or any name)
4. Click "Create"

# Option B: Use existing server
# (Skip to step 3)
```

## Step 2: Create Webhook (2 minutes)

```
1. In Discord server, right-click #general (or create new channel)
2. Create Channel → #betting-syndicate
3. Click gear icon → Edit Channel
4. Left sidebar: Integrations → Webhooks
5. Click "New Webhook"
6. Name: "Betting Syndicate Bot"
7. Click "Copy Webhook URL"
8. (Keep this copied)
```

## Step 3: Add to .env (1 minute)

```bash
# Open .env
nano .env

# Add this line (paste your webhook URL):
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID_HERE/YOUR_TOKEN_HERE

# Save (Ctrl+O, Enter, Ctrl+X)
```

## Step 4: Install Dependency

```bash
pip install aiohttp==3.9.0
```

## Step 5: Test It

```bash
# Test simple message
python -c "
import asyncio
from notification.discord_notifier import DiscordNotifier

async def test():
    notifier = DiscordNotifier()
    if notifier.enabled:
        await notifier.send_message('🎰 Test message from Bratislava Betting Syndicate!')
        print('✅ Message sent to Discord!')
    else:
        print('❌ Discord not configured')

asyncio.run(test())
"
```

You should see the message appear in Discord #betting-syndicate channel immediately.

## Step 6: Run with Discord Notifications

```bash
# Test with sample data (quick)
python main.py --games 3 --sample --no-live

# Or with live data
python main.py --daily --games 5 --no-live
```

Watch Discord for messages as agents analyze!

---

## Example Output

You'll see Discord messages like:

```
⚽ NEW GAME: Barcelona @ Real Madrid
🕐 Commence time: 2025-11-25 20:00:00
🏟️ Analyzing now...

🧠 Viktor (SHARP)
✅ Barcelona @ 1.85
💰 Stake: €150.00
🔥 Confidence: ▓▓▓▓▓▓░░░░ 65%
💭 Line moved 5 cents, indicates sharp action...

🤫 Nikolai (INSIDER)
✅ Barcelona @ 1.85
💰 Stake: €120.00
🔥 Confidence: ▓▓▓▓▓▓▓░░░ 75%
💭 I heard from a guy who knows someone...

🎲 Jozef (DEGEN)
✅ Real Madrid @ 1.92
💰 Stake: €200.00
🔥 Confidence: ▓▓▓▓▓▓▓▓▓▓ 95%
💭 Barcelona always loses on Tuesdays...

🔮 ORACLE'S DECISION
═══════════════════════════════════
🎯 Final Pick: Barcelona
🗳️ Votes: Barcelona (6) vs Real Madrid (4)
💰 Stake: €150.00
📊 Odds: 1.85
🔥 Confidence: 78%
═══════════════════════════════════
```

---

## Troubleshooting

### Nothing appears in Discord?

```bash
# Check if DISCORD_WEBHOOK_URL is set
python -c "import os; print(os.getenv('DISCORD_WEBHOOK_URL'))"

# Should print: https://discord.com/api/webhooks/...
# If blank, webhook not in .env
```

### 404 Error?

```
❌ Discord error: HTTP 404
```
Webhook was deleted or URL is wrong. Create new webhook in Discord.

### 401 Error?

```
❌ Discord error: HTTP 401
```
Webhook token is invalid. Copy full URL from Discord again.

### Test passes but main.py shows no messages?

1. Check `.env` has `DISCORD_WEBHOOK_URL`
2. Run `python main.py --games 3 --sample --no-live`
3. Look at Discord channel for messages

---

## Next: Integrate with graph.py

Once Discord is working, we need to:

1. Make agent analysis async
2. Pass notifier to SyndicateGraph
3. Emit notifications as agents complete

This will happen in the next step (DISCORD_INTEGRATION.md coming soon).

For now, just get the basic notification working!

