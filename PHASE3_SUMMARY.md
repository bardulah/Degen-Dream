# Phase 3: UX-First Degen App - Executive Summary

## The Pivot
**From**: Results tracking + Agent learning (boring infrastructure)  
**To**: Real-time dashboard, notifications, and shareable predictions (fun vibes)

**Why**: For a degen app, the fun is in the chaos and personality clashes, not in metrics. Agent learning could actually ruin what makes them entertaining.

---

## What We're Building

### 🎨 Visual Dashboard (Streamlit)
Real-time agent analysis with animated cards, confidence bars, debate streaming, and oracle decision display. Watch agents think and argue live.

### 📲 Push Notifications (Telegram/Discord)
Agent takes pushed as they analyze, not after. Full personality in messages: sharps sound analytical, degens sound chaotic, insiders sound mysterious.

### 🖼️ Shareable Predictions (Image Cards)
Generate beautiful prediction cards with agent breakdown, odds, stake, reasoning. Export as PNG for Twitter, Discord, betting groups.

### 🧠 15 Agent Personalities (vs current 10)
Add: Superstitious, Contrarian, Prop Specialist, Weather Predictor, Sentiment Tracker  
Each with unique decision-making style and chaotic energy.

### 🔧 Custom Agent Builder
Let users create their own agent personalities with custom prompts and test them on sample games before using in simulations.

### 🎰 Parlay Generator
Combine picks into 2-leg, 3-leg, N-leg parlays. Calculate combined odds and potential winnings. Perfect for degen energy.

---

## Timeline: 6.5 Hours

| Component | Time | Dependencies |
|-----------|------|--------------|
| Dashboard | 1.5h | - |
| Notifications | 1h | Dashboard done |
| Export/Sharing | 1h | - |
| New Agents | 1.5h | - |
| Custom Builder | 1h | Dashboard, New Agents |
| Parlay Generator | 1h | - |

---

## Tech Stack

**Frontend**: Streamlit + Plotly + Pillow  
**Notifications**: python-telegram-bot + Discord webhooks  
**Image Gen**: PIL (Pillow)  
**All Async**: asyncio for concurrent agent analysis  

---

## What Makes This Degen?

✅ **Personality**: Each agent has unique voice/style  
✅ **Real-time Chaos**: Watch debate unfold live  
✅ **Shareability**: Card exports for betting groups  
✅ **Visual Pop**: Neon colors, emojis, bold fonts  
✅ **Community**: Export + share creates network effect  

❌ No boring result tracking  
❌ No confidence "calibration"  
❌ No agent learning (ruins personality)  
❌ No complex metrics  

---

## Key Files to Create

```
gui/
├─ components/
│  ├─ game_card.py
│  ├─ agent_card.py
│  ├─ debate_panel.py
│  ├─ oracle_card.py
│  └─ bankroll_ticker.py
├─ streamlit_app.py (refactored)

agents/
├─ superstitious_agent.py
├─ contrarian_agent.py
├─ prop_specialist_agent.py
├─ weather_agent.py
└─ sentiment_agent.py

notification/
├─ telegram_notifier.py
└─ discord_notifier.py

export/
├─ card_generator.py
└─ parlay_generator.py

database/
└─ custom_agents.py
```

---

## Next Steps

1. Start with dashboard (most visible impact)
2. Add new agent personalities (variety)
3. Implement notifications (engagement)
4. Build export/sharing (network effect)
5. Add custom agent builder (user agency)
6. Finish with parlay generator (fun math)

All while keeping agent personalities front and center. The bots ARE the product.

