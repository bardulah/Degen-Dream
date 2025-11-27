# Research Findings: Phase 3 Technologies

## 1. Streamlit for Real-Time Dashboards

### Status: ✅ Recommended
**Why**: Perfect for rapid prototyping live dashboards without HTML/CSS/JS

### Key Findings:
- **Live Updates**: Use `st.empty()` + loops for animated components
- **Charts**: Plotly integration is native and responsive
- **Performance**: Cache results with `@st.cache_data` to avoid recomputes
- **Cards/Components**: `streamlit-antd-components` provides pre-built UI cards
- **Reactivity**: `st.session_state` for persistent state across reruns

### Implementation Pattern:
```python
placeholder = st.empty()
while game_analyzing:
    with placeholder.container():
        # Re-render UI with latest state
        show_agent_card(current_agent)
        time.sleep(0.5)  # Smooth updates
```

### Limitations:
- No true WebSocket (page reloads on updates)
- Workaround: Use `st.cache_data` + fast reloads (imperceptible to user)
- For true real-time, need separate web framework (FastAPI + React)

---

## 2. Telegram Bot Notifications

### Status: ✅ Recommended
**Library**: `python-telegram-bot` (v21.0+, fully async)

### Key Findings:
- **Async-first**: Built on `asyncio` for concurrent operations
- **Webhook or Polling**: Choose based on deployment
  - Webhook: Faster, requires public URL
  - Polling: Simpler, slight delay
- **Rich Messages**: Support formatting, emojis, buttons, file uploads
- **Rate Limiting**: Built-in; 30 messages/sec per bot

### Implementation Pattern:
```python
# Send formatted message with emoji
await bot.send_message(
    chat_id=CHAT_ID,
    text=f"🧠 {agent.name}: Betting {team} @ {odds}",
    parse_mode="HTML"
)

# Edit existing message (live updates)
await bot.edit_message_text(
    text=new_text,
    chat_id=CHAT_ID,
    message_id=msg_id
)
```

### Telegram Bot Setup:
1. Find @BotFather on Telegram
2. Send `/newbot`, name bot, get API token
3. Add token to `.env`: `TELEGRAM_BOT_TOKEN=xxx`
4. Get chat ID: Message bot, then `curl https://api.telegram.org/botTOKEN/getUpdates`

---

## 3. Discord Webhook Integration

### Status: ✅ Recommended (Simpler than python-discord.py)
**Method**: Webhook-based (no library needed)

### Key Findings:
- **Webhooks**: Simple HTTP POST, no authentication complexity
- **Embeds**: Rich formatting with colored cards, fields, images
- **Rate Limiting**: 1 webhook per channel; 10 messages/minute soft limit
- **No Library**: Just use `aiohttp` or `requests`

### Implementation Pattern:
```python
import aiohttp

async def send_discord_notification(webhook_url, message):
    payload = {
        "content": message,
        "username": "Betting Syndicate Bot"
    }
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=payload)

# With embed (rich format)
embed = {
    "title": "🔮 Oracle Pick",
    "description": "Barcelona vs Real Madrid",
    "fields": [
        {"name": "Team", "value": "Barcelona", "inline": True},
        {"name": "Odds", "value": "1.85", "inline": True},
        {"name": "Confidence", "value": "78%", "inline": True}
    ],
    "color": 16776960  # Yellow
}
```

### Discord Webhook Setup:
1. Go to Discord server settings → Webhooks
2. Create webhook for a channel
3. Copy webhook URL
4. Add to `.env`: `DISCORD_WEBHOOK_URL=https://...`

---

## 4. Image Generation for Shareable Cards

### Status: ✅ Recommended
**Library**: Pillow (PIL) for simplicity; ReportLab for fancy layouts

### Key Findings:
- **Pillow**: Simple, fast, built for drawing text/shapes on images
- **ReportLab**: Professional layouts, but more complex
- **Font Handling**: Can use system fonts or TTF files
- **Performance**: Generating 1000 cards takes ~5 seconds with Pillow

### Implementation Pattern:
```python
from PIL import Image, ImageDraw, ImageFont

def generate_card(prediction):
    # Create image
    img = Image.new('RGB', (1200, 800), color=(30, 20, 60))
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    title_font = ImageFont.truetype("arial.ttf", 60)
    body_font = ImageFont.truetype("arial.ttf", 30)
    
    # Draw text
    draw.text((50, 50), f"{prediction.team}", fill=(255, 215, 0), font=title_font)
    draw.text((50, 200), f"Odds: {prediction.odds}", fill=(200, 200, 200), font=body_font)
    
    img.save('card.png')
    return img
```

### Best Fonts for Degen Vibes:
- **Bold Sans-Serif**: Impact, Arial Black (modern, aggressive)
- **Monospace**: Courier (crypto/code aesthetic)
- **Retro**: Pixel fonts (gaming energy)

---

## 5. Async Agent Analysis

### Status: ✅ Recommended
**Libraries**: `asyncio`, `concurrent.futures`

### Key Findings:
- **Concurrent Agents**: Run all 10 agents in parallel, not sequentially
- **Speed**: 10 agents → 30 seconds (parallel) vs 300 seconds (sequential)
- **Gather Pattern**: Use `asyncio.gather()` for multiple concurrent tasks
- **Error Handling**: Each agent failure doesn't block others

### Implementation Pattern:
```python
import asyncio

async def analyze_game_async(agents, game):
    tasks = [agent.analyze_game_async(game) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if r is not None]

# In simulation:
bets = await analyze_game_async(syndicate.agents, game)
```

### Modify `BaseAgent`:
```python
class BaseAgent:
    async def analyze_game_async(self, game, context):
        """Async version of analyze_game"""
        # Use async LLM calls (OpenRouter has async support)
        response = await self.client.acompletion(...)
        return self._parse_response(response)
```

---

## 6. Streamlit with Async

### Status: ⚠️ Tricky (Streamlit isn't async-native)

### Key Findings:
- **Workaround**: Use `asyncio.run()` in Streamlit callbacks
- **Better**: Use ThreadPoolExecutor for background analysis
- **Best**: Move async to FastAPI, Streamlit calls FastAPI endpoint

### Recommended Approach:
```python
# gui/streamlit_app.py
import streamlit as st
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

def run_async_simulation():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_simulation_async())
        return result
    finally:
        loop.close()

if st.button("Start Simulation"):
    future = executor.submit(run_async_simulation)
    with st.spinner("Agents analyzing..."):
        result = future.result(timeout=300)
    st.success("Done!")
```

---

## 7. Database for Custom Agents

### Status: ✅ Ready (SQLAlchemy exists)

### Implementation:
```python
# database/schema.py
class CustomAgent(Base):
    __tablename__ = "custom_agents"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    name = Column(String, unique=True)
    personality_prompt = Column(Text)
    strategy = Column(String)  # conservative, balanced, aggressive
    created_at = Column(DateTime, default=datetime.utcnow)
    used_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User")
```

---

## 8. Parlay Calculation Logic

### Status: ✅ Simple Math

### Implementation:
```python
def combine_odds(*odds):
    """Multiply odds for parlay"""
    result = 1.0
    for odd in odds:
        result *= odd
    return result

def calculate_parlay(picks, stake):
    """Calculate parlay outcome"""
    combined_odds = combine_odds(*[p.odds for p in picks])
    potential_win = stake * combined_odds
    roi = ((potential_win - stake) / stake) * 100
    
    return {
        "combined_odds": combined_odds,
        "stake": stake,
        "potential_win": potential_win,
        "roi": roi,
        "num_legs": len(picks)
    }

# Example:
picks = [Bet(odds=1.85), Bet(odds=1.88), Bet(odds=1.90)]
result = calculate_parlay(picks, 100)
# combined_odds: 6.24
# potential_win: €624
```

---

## Dependencies to Install

```bash
# Core
pip install streamlit==1.28.1
pip install plotly==5.17.0
pip install pillow==10.0.0

# Notifications
pip install python-telegram-bot==21.0.1
pip install aiohttp==3.9.0

# UI Components
pip install streamlit-antd-components==0.2.2
pip install streamlit-elements==0.1.0

# Export
pip install reportlab==4.0.7
pip install qrcode==7.4.2

# Database (existing)
# SQLAlchemy already installed

# Image fonts (system-dependent)
# Linux: apt-get install fonts-liberation fonts-liberation2
# macOS: System fonts available
# Windows: System fonts available
```

---

## Summary: Which Tech to Use?

| Feature | Technology | Confidence | Notes |
|---------|-----------|-----------|-------|
| Dashboard | Streamlit + Plotly | ✅ High | Proven, fast to build |
| Notifications | python-telegram-bot | ✅ High | Async, reliable, mature |
| Discord | Webhook + aiohttp | ✅ High | Simpler than discord.py |
| Images | Pillow | ✅ High | Lightweight, fast |
| Async Agents | asyncio | ✅ High | Native Python, works well |
| Custom Agents | SQLAlchemy (existing) | ✅ High | Already in use |
| Parlays | Plain Python math | ✅ High | No library needed |

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Streamlit page reloads slow | Medium | Cache heavily, use `st.session_state` |
| Telegram rate limiting | Low | Queue messages, stagger sends |
| Agent analysis takes too long | Medium | Async + parallel execution |
| Pillow font rendering | Low | Use system fonts, fallback to default |
| Discord webhook outage | Low | Graceful fallback, silent fail |

---

## Performance Estimates

- **10 Agents Analysis (async)**: 25-30 seconds
- **Streamlit Dashboard Render**: 500ms
- **Image Card Generation**: 100ms
- **Telegram Send**: 500ms per message
- **Total Pipeline**: ~45 seconds end-to-end

---

