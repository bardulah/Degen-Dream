# Discord Notifications Implementation Guide

## Quick Start

### 1. Create Discord Server & Webhook

```bash
# Manual steps:
1. Create new Discord server (or use existing)
2. Create channel: #betting-syndicate
3. Server Settings → Integrations → Webhooks
4. Create Webhook for #betting-syndicate
5. Copy webhook URL
6. Add to .env: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. Install Dependencies
```bash
pip install aiohttp==3.9.0
```

### 3. Create Discord Notifier

```python
# notification/discord_notifier.py
import aiohttp
import asyncio
import os
from typing import Optional, Dict, Any
from datetime import datetime

class DiscordNotifier:
    """Send real-time notifications to Discord webhook"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize Discord notifier
        
        Args:
            webhook_url: Discord webhook URL (defaults to env var)
        """
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            print("⚠️  Discord webhook not configured")
    
    async def send_message(self, content: str):
        """Send plain text message"""
        if not self.enabled:
            return
        
        payload = {"content": content, "username": "Betting Syndicate"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status != 204:
                        print(f"Discord error: {resp.status}")
        except Exception as e:
            print(f"Discord send failed: {e}")
    
    async def send_embed(self, title: str, fields: Dict[str, str], 
                        color: int = 16776960, thumbnail_url: str = None):
        """Send rich embed message with fields
        
        Args:
            title: Embed title
            fields: Dict of field_name -> field_value
            color: Decimal color code (e.g., 16776960 for gold)
            thumbnail_url: URL for small image
        """
        if not self.enabled:
            return
        
        embed_fields = [
            {"name": k, "value": str(v), "inline": True}
            for k, v in fields.items()
        ]
        
        embed = {
            "title": title,
            "fields": embed_fields,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}
        
        payload = {"embeds": [embed], "username": "Betting Syndicate"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status != 204:
                        print(f"Discord error: {resp.status}")
        except Exception as e:
            print(f"Discord send failed: {e}")
    
    # Agent-specific methods
    
    async def on_game_start(self, game):
        """Notify when game analysis starts"""
        await self.send_message(
            f"⚽ **NEW GAME**: {game.away_team} @ {game.home_team}\n"
            f"🕐 **Starting analysis**..."
        )
    
    async def on_agent_analyzed(self, agent_name: str, agent_type: str, bet):
        """Notify when agent finishes analysis"""
        
        emoji_map = {
            "sharp": "🧠",
            "insider": "🤫",
            "degen": "🎲",
            "bookie": "📊"
        }
        emoji = emoji_map.get(agent_type, "🤖")
        
        if bet is None:
            await self.send_message(
                f"{emoji} **{agent_name}** ({agent_type.upper()})\n"
                f"❌ Pass - No value found"
            )
        else:
            confidence_bar = self._confidence_bar(bet.confidence)
            await self.send_message(
                f"{emoji} **{agent_name}** ({agent_type.upper()})\n"
                f"✅ **{bet.team}** @ {bet.odds:.2f}\n"
                f"💰 Stake: €{bet.stake:.2f}\n"
                f"🔥 Confidence: {confidence_bar} {bet.confidence:.0%}\n"
                f"💭 {bet.reasoning}"
            )
    
    async def on_debate_message(self, agent_name: str, message: str):
        """Notify during debate phase"""
        await self.send_message(
            f"🗣️  **{agent_name}**\n{message}"
        )
    
    async def on_oracle_decision(self, consensus_bet, agent_votes: Dict[str, int]):
        """Notify when Oracle makes final decision"""
        
        vote_text = " vs ".join([
            f"{team} ({votes})" 
            for team, votes in sorted(agent_votes.items(), key=lambda x: x[1], reverse=True)
        ])
        
        color_map = {
            "home": 3066993,      # Green
            "away": 15158332      # Red
        }
        color = color_map.get(consensus_bet.team, 16776960)
        
        await self.send_embed(
            title=f"🔮 ORACLE'S WISDOM",
            fields={
                "Final Pick": f"**{consensus_bet.team}**",
                "Vote Count": vote_text,
                "Stake": f"€{consensus_bet.stake:.2f}",
                "Odds": f"{consensus_bet.odds:.2f}",
                "Confidence": f"{consensus_bet.confidence:.0%}",
                "Reasoning": consensus_bet.reasoning[:200]  # Truncate
            },
            color=color
        )
    
    async def on_simulation_start(self, num_games: int, sport: str):
        """Notify when simulation starts"""
        await self.send_message(
            f"🚀 **SIMULATION STARTED**\n"
            f"📊 Games: {num_games}\n"
            f"⚽ Sport: {sport.upper()}"
        )
    
    async def on_simulation_complete(self, num_games: int, total_wagered: float):
        """Notify when simulation completes"""
        await self.send_message(
            f"✅ **SIMULATION COMPLETE**\n"
            f"📊 Games Analyzed: {num_games}\n"
            f"💰 Total Wagered: €{total_wagered:.2f}"
        )
    
    # Utility
    
    @staticmethod
    def _confidence_bar(confidence: float, length: int = 10) -> str:
        """Generate confidence bar"""
        filled = int(confidence * length)
        return "▓" * filled + "░" * (length - filled)


# Color codes for Discord embeds (decimal format)
COLORS = {
    "gold": 16776960,      # Gold
    "green": 3066993,      # Green
    "red": 15158332,       # Red
    "blue": 3447003,       # Blue
    "purple": 9807270,     # Purple
    "orange": 15105570,    # Orange
}
```

### 4. Integrate with graph.py

```python
# simulation/graph.py - Modify SyndicateGraph class

from notification.discord_notifier import DiscordNotifier
import asyncio

class SyndicateGraph:
    def __init__(self, agents=None, bankroll_manager=None, db=None, 
                 simulation_id=None, notifier=None):
        # ... existing code ...
        self.notifier = notifier
    
    async def _gather_proposals_async(self, state):
        """Async version of _gather_proposals with Discord notifications"""
        game = state["game"]
        context = state.get("market_context", {})
        agent_bets = []
        
        if self.notifier:
            await self.notifier.on_game_start(game)
        
        tasks = []
        for agent in self.agents:
            task = asyncio.create_task(self._analyze_agent_async(agent, game, context))
            tasks.append((agent, task))
        
        # Gather results as they complete
        for agent, task in tasks:
            try:
                bet = await task
                if bet:
                    agent_bets.append(bet)
                
                # Notify Discord immediately
                if self.notifier:
                    await self.notifier.on_agent_analyzed(
                        agent.name, 
                        agent.agent_type.value, 
                        bet
                    )
            except Exception as e:
                print(f"Error analyzing {agent.name}: {e}")
        
        state["agent_bets"] = agent_bets
        return state
    
    async def _analyze_agent_async(self, agent, game, context):
        """Async wrapper for agent analysis"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        bet = await loop.run_in_executor(None, agent.analyze_game, game, context)
        return bet
```

### 5. Modify main.py to use Discord

```python
# main.py - Add Discord notifier

from notification.discord_notifier import DiscordNotifier

def main(...):
    # ... existing code ...
    
    # Initialize Discord notifier
    discord_notifier = DiscordNotifier()
    
    if discord_notifier.enabled:
        print("📢 Discord notifications enabled")
        asyncio.run(discord_notifier.on_simulation_start(num_games, sport))
    
    # Pass to simulation
    results = run_simulation(
        games=games,
        num_games=num_games,
        starting_bankroll=settings.STARTING_BANKROLL,
        monitor=monitor,
        db=db,
        user_id=user.id,
        simulation_id=simulation_id,
        sport=sport,
        use_live_data=not use_sample_data,
        notifier=discord_notifier  # NEW
    )
    
    # Notify completion
    if discord_notifier.enabled:
        asyncio.run(discord_notifier.on_simulation_complete(
            num_games, 
            results.get("total_wagered", 0)
        ))
```

### 6. Modify run_simulation function

```python
# simulation/graph.py - run_simulation function

def run_simulation(
    games: List[Game],
    num_games: int = 100,
    starting_bankroll: float = 10000,
    monitor: Optional[Any] = None,
    db: Optional[Session] = None,
    user_id: Optional[str] = None,
    simulation_id: Optional[str] = None,
    sport: str = "unknown",
    use_live_data: bool = False,
    notifier: Optional[DiscordNotifier] = None  # NEW
) -> Dict[str, Any]:
    
    # ... existing code ...
    
    syndicate = SyndicateGraph(
        bankroll_manager=None,
        db=db,
        simulation_id=simulation_id,
        notifier=notifier  # Pass notifier
    )
    
    # ... rest of function ...
```

---

## Testing Discord Integration

### Test 1: Simple Message
```python
# test_discord.py
import asyncio
from notification.discord_notifier import DiscordNotifier

async def test_simple():
    notifier = DiscordNotifier()
    if not notifier.enabled:
        print("Configure DISCORD_WEBHOOK_URL in .env")
        return
    
    await notifier.send_message("🎰 Test message from Bratislava Betting Syndicate")
    print("✅ Message sent")

asyncio.run(test_simple())
```

### Test 2: Embed with Fields
```python
async def test_embed():
    notifier = DiscordNotifier()
    
    await notifier.send_embed(
        title="🧠 Agent Analysis Test",
        fields={
            "Agent": "Viktor (Sharp)",
            "Pick": "Barcelona",
            "Odds": "1.85",
            "Confidence": "78%"
        },
        color=16776960  # Gold
    )
    print("✅ Embed sent")

asyncio.run(test_embed())
```

### Test 3: Full Simulation
```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
python main.py --daily --games 3 --no-live
```

You should see:
1. Simulation start message in Discord
2. Agent analysis messages as they complete
3. Oracle decision message
4. Simulation complete message

---

## Discord Message Examples

### Agent Analysis
```
🧠 Viktor (Sharp)
✅ Barcelona @ 1.85
💰 Stake: €150.00
🔥 Confidence: ▓▓▓▓▓▓░░░░ 65%
💭 Line moved 5 cents to Barcelona, indicates sharp action on the home team
```

### Degen Agent
```
🎲 Jozef (Degen)
✅ Real Madrid @ 1.92
💰 Stake: €200.00
🔥 Confidence: ▓▓▓▓▓▓▓▓▓▓ 95%
💭 🎲 DEGEN ENERGY: Barcelona always loses on weekends, trust me bro
```

### Oracle Decision (Embed)
```
═══════════════════════════════════
🔮 ORACLE'S WISDOM
═══════════════════════════════════
Final Pick: Barcelona
Vote Count: Barcelona (6) vs Real Madrid (4)
Stake: €150.00
Odds: 1.85
Confidence: 78%
Reasoning: Barcelona in great form, Madrid missing key players...
═══════════════════════════════════
```

---

## Emoji Reference

```python
AGENT_EMOJIS = {
    "sharp": "🧠",      # Brain = analytical
    "insider": "🤫",    # Shh = secretive
    "degen": "🎲",      # Dice = chaotic
    "bookie": "📊"      # Chart = market data
}

CONTEXT_EMOJIS = {
    "game": "⚽",       # Soccer ball
    "start": "🚀",      # Rocket
    "complete": "✅",   # Checkmark
    "decision": "🔮",   # Crystal ball
    "warning": "⚠️",    # Warning
    "money": "💰",      # Money
    "confidence": "🔥", # Fire
    "debate": "🗣️",     # Speech
}
```

---

## Environment Setup

Add to `.env`:
```bash
# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

Get webhook URL:
1. Discord Server Settings → Integrations → Webhooks
2. Create Webhook for #betting-syndicate channel
3. Copy webhook URL
4. Paste into .env

---

## Next Steps

Once Discord is working:
1. Test with `--sample` flag for quick feedback
2. Add debate phase notifications (optional)
3. Move to Dashboard (Streamlit)
4. Add Telegram (similar to Discord)
5. Build image export

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 404 Webhook Error | Check webhook URL is correct, webhook hasn't been deleted |
| 401 Unauthorized | Webhook URL is malformed |
| Rate limited | Space out messages, webhook allows ~1 per second |
| No messages appear | Discord webhook URL not set in .env |
| Async error | Make sure `asyncio` import is at top of file |

