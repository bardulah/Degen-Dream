# Phase 3: UX-First Degen App Implementation Plan

## Overview
Shift from results/learning tracking to building an engaging, visually fun betting prediction platform. Focus on real-time visualizations, agent personalities, and shareable content.

---

## PHASE 3A: Dashboard & Real-Time Notifications (3-4 hours)

### 1. Streamlit Dashboard Overhaul
**Goal**: Replace basic console output with interactive, real-time visualization

**Tech Stack**:
- Streamlit 1.28+
- Plotly (for interactive charts)
- Streamlit-elements (for custom layouts)
- Streamlit-antd-components (for cards/badges)

**Components to Build**:

#### A. Game Card Component
```python
# gui/components/game_card.py
def show_game_card(game: Game):
    """Display matchup with odds"""
    - Home team name & logo placeholder
    - Away team name & logo placeholder  
    - Odds for both sides
    - Commence time
    - Sport badge
```

#### B. Agent Response Card Component
```python
# gui/components/agent_card.py
def show_agent_card(agent_name, agent_type, response, decision):
    """Real-time agent analysis card"""
    - Agent name + emoji (🧠 Sharp, 🤫 Insider, 🎲 Degen, 📊 Bookie)
    - Typing animation as agent thinks
    - Final decision box (team, stake, confidence)
    - Confidence bar (0-100%)
    - Reasoning quote (colored by agent type)
```

#### C. Debate Streaming Component
```python
# gui/components/debate_panel.py
def show_debate_stream(debate_history):
    """Live debate panel"""
    - Agent names with reactions
    - Statement appears as it's spoken
    - Pros/cons sidebar
    - Final vote counts with emojis
```

#### D. Oracle Decision Card
```python
# gui/components/oracle_card.py
def show_oracle_decision(consensus_bet, vote_breakdown):
    """Final pick announcement"""
    - Team being backed (big, bold)
    - Vote breakdown pie chart (4 votes home, 3 votes away)
    - Stake & confidence stats
    - Agent who proposed it
```

#### E. Bankroll Ticker (Live Update)
```python
# gui/components/bankroll_ticker.py
def show_bankroll_ticker(initial_bankroll, current_bankroll):
    """Running bankroll with animated changes"""
    - Current balance (green if +, red if -)
    - Change since start (€ amount)
    - ROI % (if bets have been placed)
```

**Streamlit Layout**:
```
┌─ Header ────────────────────────────────┐
│  🎰 Bratislava Betting Syndicate       │
│  Live Prediction Dashboard             │
│  👥 10 Agents Ready  💾 Connected      │
└─────────────────────────────────────────┘

┌─ Main Content ───────────────────────────┐
│  [Game 1 of 5] Barcelona vs Real Madrid │
│                                          │
│  ┌─ Agents Analyzing ───────────────┐   │
│  │ 🧠 Viktor (Sharp)           [▓▓░]│   │ (confidence bar)
│  │  → Analyzing line movements     │   │
│  │                                 │   │
│  │ 🤫 Nikolai (Insider)        [▓▓▓]│   │
│  │  → I heard from a guy...       │   │
│  │                                 │   │
│  │ 🎲 Jozef (Degen)           [▓▓▓▓]│   │
│  │  → FULL SEND MODE!             │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─ Debate Live ────────────────────┐   │
│  │ Viktor: "Actually, the odds are│   │
│  │ too tight here for value..."   │   │
│  │                                 │   │
│  │ Jozef: "You math nerds ruin    │   │
│  │ the fun! Barcelona has VIBES!" │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─ 🔮 Oracle's Wisdom ─────────────┐   │
│  │ FINAL PICK: Barcelona          │   │
│  │ Votes: 4/10 agents             │   │
│  │ Stake: €150 @ 1.85             │   │
│  │ Confidence: 78%                │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘

┌─ Sidebar ────────────────────────────────┐
│ 💰 Bankroll: €9,850 (-€150)             │
│ 📊 Games: 1/5 Analyzed                  │
│ ✅ Bets Placed: 1                       │
│ 📈 ROI: -1.5%                           │
│                                          │
│ [📥 Export CSV] [🖼️ Share Card] [📧]   │
└─────────────────────────────────────────┘
```

**Implementation Steps**:
1. Create `gui/components/` directory with modular card components
2. Modify `simulation/graph.py` to emit live updates via callbacks
3. Build main dashboard in `gui/streamlit_app.py` with tabs:
   - Live (current game analysis)
   - History (past games)
   - Stats (agent performance)
4. Add CSS/theming for degen aesthetic (neon colors, bold fonts)

**Time**: 1.5 hours

---

### 2. Telegram/Discord Real-Time Notifications
**Goal**: Push agent takes as they happen (not after all done)

**Tech Stack**:
- python-telegram-bot (2.x async)
- Discord.py or webhook (simpler)
- APScheduler for scheduled tasks

**Flow**:
```
Agent Analyzes Game
    ↓
Emit to Telegram/Discord
    ├─ "[Sharp] Viktor analyzing Barcelona vs Madrid..."
    ├─ "[Insider] Nikolai: I heard something 🤫"
    └─ "[Degen] Jozef: SEND IT 🎲"
    ↓
Debate Happens
    └─ Post debate highlights
    ↓
Oracle Decides
    └─ 🔮 PICK: Barcelona 4-3 votes €150 @ 1.85
```

**Implementation**:
```python
# notification/telegram_notifier.py
class TelegramNotifier:
    async def on_agent_analyzed(self, agent_name, decision):
        emoji = self.get_agent_emoji(agent_name)
        text = f"{emoji} {agent_name}: {decision.team} @ {decision.odds}"
        await self.send_message(text)
    
    async def on_oracle_decided(self, consensus_bet):
        text = f"🔮 ORACLE PICK: {consensus_bet.team}\n" \
               f"Stakes: €{consensus_bet.stake}\n" \
               f"Confidence: {consensus_bet.confidence:.0%}"
        await self.send_message(text, disable_preview=False)

# notification/discord_notifier.py
class DiscordNotifier:
    async def send_embed(self, title, fields):
        embed = discord.Embed(title=title, color=discord.Color.gold())
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
        await self.webhook.send(embed=embed)
```

**Modify graph.py**:
```python
# simulation/graph.py
class SyndicateGraph:
    async def _gather_proposals_async(self, state, notifier):
        for agent in self.agents:
            bet = await agent.analyze_game_async(game)
            if notifier:
                await notifier.on_agent_analyzed(agent.name, bet)
```

**Time**: 1 hour

---

### 3. Prediction Sharing & Export
**Goal**: Generate shareable prediction cards for Twitter, Discord, betting groups

**Tech Stack**:
- Pillow (PIL) for image generation
- reportlab for fancy cards
- qrcode for shareable links

**Output Formats**:

#### A. Shareable Image Card
```
┌────────────────────────────────┐
│  🎰 DEGEN PREDICTION CARD 🎰  │
│                                │
│  Barcelona vs Real Madrid      │
│  ⚽ La Liga • Oct 25, 2025    │
│                                │
│  🔮 ORACLE PICK:               │
│  Barcelona (4 vs 3 agents)     │
│                                │
│  💰 Stake: €150               │
│  📊 Odds: 1.85                │
│  🔥 Confidence: 78%            │
│                                │
│  ┌──────────────────────────┐  │
│  │ Agent Breakdown:         │  │
│  │ 🧠 Sharps: 2-1          │  │
│  │ 🤫 Insiders: 1-1        │  │
│  │ 🎲 Degens: 2-1          │  │
│  │ 📊 Bookies: 1-0         │  │
│  └──────────────────────────┘  │
│                                │
│  Top Reasoning:                │
│  "Barcelona in great form,     │
│   injuries hurt Madrid"        │
│                                │
│  Share: degen.app/pred/abc123  │
└────────────────────────────────┘
```

#### B. CSV Export
```csv
game,pick,stake,confidence,odds,agent_reasoning
"Barcelona vs Madrid",Barcelona,150,0.78,1.85,"..."
```

#### C. HTML Snapshot
```python
# export/html_exporter.py
def generate_html_card(prediction):
    return f"""
    <html>
        <head><style>body {{ font-family: Arial; background: #1a1a1a; color: #fff; }}</style></head>
        <body>
            <div class="card">
                <h1>🔮 Prediction Card</h1>
                <p>Pick: {prediction.team}</p>
                <p>Odds: {prediction.odds}</p>
            </div>
        </body>
    </html>
    """
```

**Implementation**:
```python
# export/card_generator.py
from PIL import Image, ImageDraw, ImageFont

def generate_prediction_card(prediction: Bet, game: Game):
    # Create blank image (1200x800, degen purple)
    img = Image.new('RGB', (1200, 800), color=(30, 20, 60))
    draw = ImageDraw.Draw(img)
    
    # Add game info
    draw.text((50, 50), f"{game.away_team} vs {game.home_team}", 
              fill=(255, 255, 255), font=large_font)
    
    # Add oracle pick (BIG)
    draw.text((400, 200), f"🔮 {prediction.team}", 
              fill=(255, 215, 0), font=huge_font)
    
    # Add stats
    draw.text((50, 400), f"Stake: €{prediction.stake}", fill=(200, 200, 200))
    draw.text((50, 450), f"Confidence: {prediction.confidence:.0%}", fill=(200, 200, 200))
    
    img.save('prediction_card.png')
    return img

# export/exporter.py
class PredictionExporter:
    def export_image(self, prediction, game):
        return generate_prediction_card(prediction, game)
    
    def export_csv(self, predictions, filename="predictions.csv"):
        df = pd.DataFrame([p.__dict__ for p in predictions])
        df.to_csv(filename)
    
    def export_html(self, predictions, filename="predictions.html"):
        # Generate HTML snapshot
        pass
```

**Time**: 1 hour

---

## PHASE 3B: Agent Expansion (2-3 hours)

### 4. More Agent Personalities
**Goal**: Add 5 new agent archetypes to increase chaos and variety

**New Agent Types**:

#### A. Superstitious Agent
```python
# agents/superstitious_agent.py
class SuperstitiousAgent(BaseAgent):
    """Bets based on moon phases, lucky numbers, horoscopes"""
    
    def analyze_game(self, game, context):
        moon_phase = self._get_moon_phase()  # waxing, waning, full, new
        lucky_today = self._get_lucky_numbers()  # [3, 7, 13]
        horoscope = self._get_zodiac_match(game)
        
        prompt = f"""You are a superstitious bettor.
        Moon phase: {moon_phase}
        Lucky numbers today: {lucky_today}
        Team zodiac signs: {horoscope}
        
        Should we bet? Use VIBES not logic."""
```

#### B. Contrarian Agent
```python
# agents/contrarian_agent.py
class ContrarianAgent(BaseAgent):
    """Fades the crowd, loves underdogs"""
    
    def analyze_game(self, game, context):
        public_betting = context.get("public_betting", {})
        public_side = "home" if public_betting["home"] > 60 else "away"
        opposite_side = "away" if public_side == "home" else "home"
        
        prompt = f"""You're a contrarian.
        The public is betting {public_betting['home']:.0f}% on home.
        So you should fade that side.
        Love underdogs, hate favorites."""
```

#### C. Prop Bet Specialist
```python
# agents/prop_specialist_agent.py
class PropSpecialistAgent(BaseAgent):
    """Focuses on player stats, injury angles, prop bets"""
    
    def analyze_game(self, game, context):
        injuries = context.get("injuries", [])
        form_stats = context.get("player_form", {})
        
        prompt = f"""You're a prop specialist.
        Focus on: player injuries, streak stats, prop bet angles.
        Injuries: {injuries}
        In-form players: {form_stats}
        Look for edge in individual player performance."""
```

#### D. Weather Predictor
```python
# agents/weather_agent.py
class WeatherPredictorAgent(BaseAgent):
    """Analyzes weather impact on game"""
    
    def analyze_game(self, game, context):
        weather = context.get("weather", {})
        # wind, rain, snow, temp impact analysis
        
        prompt = f"""You're a weather expert.
        Forecast: {weather}
        How does wind/rain/cold affect the game style?
        Which team benefits from these conditions?"""
```

#### E. Social Sentiment Tracker
```python
# agents/sentiment_agent.py
class SocialSentimentAgent(BaseAgent):
    """Tracks Reddit/Twitter vibes"""
    
    def analyze_game(self, game, context):
        reddit_sentiment = context.get("reddit_sentiment", "neutral")
        twitter_vibes = context.get("twitter_trending", [])
        
        prompt = f"""You read Reddit and Twitter.
        Vibes on r/soccer: {reddit_sentiment}
        Twitter trending: {twitter_vibes}
        What's the crowd thinking? Follow the momentum."""
```

**Implementation Steps**:
1. Create base classes in `agents/` directory
2. Add personality prompts to `config/settings.py`
3. Update `simulation/graph.py` to initialize 15 agents instead of 10
4. Test with `--sample` flag

**Time**: 1.5 hours

---

### 5. Custom Agent Builder UI
**Goal**: Let users create and test their own agent personalities

**UI Flow**:
```
Custom Agent Builder
└─ Personality Prompt Editor (text area)
└─ Strategy Selector (dropdown)
   ├─ Conservative (low risk, high conviction)
   ├─ Balanced (middle ground)
   ├─ Aggressive (high risk, go big)
   └─ Random (chaos mode)
└─ Test Runner (load sample game)
   └─ See analysis in real-time
└─ Save Button (store to database)
└─ Use in Next Simulation (checkbox)
```

**Implementation**:
```python
# gui/streamlit_app.py - Custom Agent Tab
if st.sidebar.radio("", ["Live Dashboard", "Custom Agent"]) == "Custom Agent":
    st.header("🔧 Custom Agent Builder")
    
    agent_name = st.text_input("Agent Name", "My Agent")
    personality = st.text_area("Personality Prompt", 
        "You are a betting agent...", height=200)
    strategy = st.selectbox("Strategy", 
        ["Conservative", "Balanced", "Aggressive", "Random"])
    
    if st.button("🧪 Test on Sample Game"):
        agent = create_custom_agent(agent_name, personality, strategy)
        game = load_sample_game()
        result = agent.analyze_game(game, {})
        
        st.json({
            "team": result.team,
            "stake": result.stake,
            "confidence": result.confidence,
            "reasoning": result.reasoning
        })
    
    if st.button("💾 Save Agent"):
        save_agent_to_db(agent_name, personality, strategy)
        st.success(f"✅ Saved {agent_name}!")
    
    if st.checkbox("Use in next simulation"):
        st.session_state.custom_agent = agent_name

# database/custom_agents.py
class CustomAgent(Base):
    __tablename__ = "custom_agents"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.id"))
    name = Column(String)
    personality_prompt = Column(Text)
    strategy = Column(String)  # conservative, balanced, aggressive
    created_at = Column(DateTime)
    used_count = Column(Integer, default=0)
```

**Time**: 1 hour

---

## PHASE 3C: Parlay Generator (1-2 hours)

### 6. Parlay Generator
**Goal**: Combine picks into parlays for degen energy

**UI**:
```
Parlay Generator
├─ Select picks from prediction history
│  ├─ Barcelona ML @ 1.85
│  ├─ Over 2.5 @ 1.88
│  └─ Real Madrid Spread -1.5 @ 1.90
│
├─ Parlay Options
│  ├─ 2-Leg Parlay
│  ├─ 3-Leg Parlay
│  ├─ Custom Parlay
│
├─ Calculate
│  ├─ Combined Odds: 6.24 (1.85 × 1.88 × 1.78)
│  ├─ Potential Win: €624 on €100 stake
│  ├─ Risk/Reward: 6:1
│
└─ [📥 Export Parlay] [💾 Save] [🚀 Place Bet]
```

**Implementation**:
```python
# export/parlay_generator.py
class ParlayGenerator:
    def combine_bets(self, bets: List[Bet], stake: float) -> Dict:
        """Combine picks into parlays"""
        combined_odds = 1.0
        for bet in bets:
            combined_odds *= bet.odds
        
        potential_win = stake * combined_odds
        roi = (potential_win - stake) / stake * 100
        
        return {
            "picks": [f"{b.team} @ {b.odds}" for b in bets],
            "combined_odds": combined_odds,
            "stake": stake,
            "potential_win": potential_win,
            "roi": roi,
            "num_legs": len(bets)
        }
    
    def generate_all_parlays(self, bets: List[Bet], stake: float):
        """Generate all possible 2-leg, 3-leg, etc combos"""
        from itertools import combinations
        
        results = []
        for leg_count in [2, 3, len(bets)]:
            for combo in combinations(bets, leg_count):
                results.append(self.combine_bets(list(combo), stake))
        
        return sorted(results, key=lambda x: x["roi"], reverse=True)

# gui/streamlit_app.py - Parlay Tab
if "Parlay" in tabs:
    st.header("📈 Parlay Generator")
    
    # Load recent predictions
    predictions = load_recent_predictions()
    
    selected = st.multiselect("Select picks", 
        [f"{p.game} - {p.team}" for p in predictions],
        default=[predictions[0].game] if predictions else [])
    
    stake = st.number_input("Stake (€)", 100, step=10)
    
    if st.button("🧮 Calculate"):
        bets = [p for p in predictions if p.game in selected]
        parlays = ParlayGenerator().generate_all_parlays(bets, stake)
        
        for i, parlay in enumerate(parlays[:5], 1):  # Top 5
            st.metric(
                f"{parlay['num_legs']}-Leg",
                f"{parlay['combined_odds']:.2f}",
                f"€{parlay['potential_win']:.2f} (+{parlay['roi']:.0f}%)"
            )
```

**Time**: 1 hour

---

## SUMMARY: Estimated Timeline

| Phase | Task | Hours | Status |
|-------|------|-------|--------|
| 3A | Streamlit Dashboard | 1.5 | Pending |
| 3A | Telegram/Discord Notifications | 1 | Pending |
| 3A | Prediction Sharing/Export | 1 | Pending |
| 3B | New Agent Personalities | 1.5 | Pending |
| 3B | Custom Agent Builder UI | 1 | Pending |
| 3C | Parlay Generator | 1 | Pending |
| **Total** | | **6.5 hours** | |

---

## Technology Stack Summary

```
Frontend:
├─ Streamlit 1.28+
├─ Plotly (interactive charts)
├─ Streamlit-antd-components (cards)
└─ Pillow (image generation)

Backend:
├─ python-telegram-bot (async)
├─ discord.py (webhooks)
└─ asyncio (concurrent agent analysis)

Database:
└─ SQLAlchemy ORM (existing)

New Dependencies to Install:
┌─────────────────────────────────────┐
│ pip install streamlit==1.28.1       │
│ pip install plotly==5.17.0          │
│ pip install pillow==10.0.0          │
│ pip install python-telegram-bot     │
│ pip install discord.py              │
│ pip install streamlit-antd-components│
│ pip install streamlit-elements      │
│ pip install reportlab==4.0.7        │
│ pip install qrcode==7.4.2           │
│ pip install aiohttp                 │
└─────────────────────────────────────┘
```

---

## Implementation Order (Priority)

1. **Dashboard (3A-1)** - Core UX foundation
2. **Notifications (3A-2)** - Real-time engagement
3. **New Agents (3B-1)** - Personality variety
4. **Export (3A-3)** - Shareable content
5. **Custom Builder (3B-2)** - User agency
6. **Parlay Generator (3C)** - Degen energy

---

## Success Metrics

✅ Dashboard loads predictions in real-time with live agent cards
✅ Telegram/Discord receives agent takes as they happen
✅ Users can export prediction images for Twitter/Discord
✅ 15+ agent personalities with distinct vibes
✅ Custom agent builder tested and working
✅ Parlay combos calculated correctly
✅ Full end-to-end flow: analysis → dashboard → export → share

