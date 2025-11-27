# Discord Integration - Fixes Applied

## Issues Fixed

### 1. Sport Name Display
**Problem:** Sport displayed as "SOCCER_EPL" (raw API code)
**Solution:** Added `format_sport_name()` utility that converts:
- `soccer_epl` → Soccer - EPL
- `soccer_la_liga` → Soccer - La Liga
- `nba` → NBA
- `multi-sport` → Multi-Sport
- etc.

### 2. Matchup Information Missing
**Problem:** Oracle decision only showed predicted team, not the matchup
**Solution:** Added "⚽ Matchup" field to oracle Discord embed showing "Away Team @ Home Team"

### 3. Vote Field Empty
**Problem:** Votes field showed empty in Discord message
**Solution:** 
- Modified `SyndicateState` TypedDict to include `agent_votes: Dict[str, int]`
- Updated `_oracle_decides()` to return `(best_bet, team_votes)` tuple
- Updated `_vote()` to capture and store vote breakdown in state
- Pass actual vote data to Discord notifier

### 4. Reasoning Truncated
**Problem:** Reasoning was cut off to 200 characters
**Solution:** 
- Removed aggressive truncation
- Changed to 500 character limit with "..." ellipsis
- Kept full reasoning in chat-style debate messages (up to 1900 chars before Discord 2000 char limit)

## About the Oracle

**The Oracle is NOT LLM-based.** It's a deterministic voting algorithm:

1. **Gather Phase**: All 10 agents analyze the game independently (using LLM)
2. **Debate Phase**: First 5 agents discuss (using LLM) 
3. **Vote Phase**: Each agent votes for their preferred team (1 vote each = democratic)
4. **Oracle Decision** (DETERMINISTIC):
   - Count votes for each team
   - Team with most votes wins
   - Among bets on winning team, pick the one with highest conviction (stake + confidence)
   - No LLM involved - it's a mathematical selection function

**Why this design?**
- Removes bias that comes from a single LLM picking the final bet
- Democratic: all agent perspectives matter equally
- Conviction-based: rewards confident, high-stakes picks
- Transparent: vote counts clearly shown in Discord

## Discord Integration Architecture

### Full Chat Flow (Next Phase)

The Discord channel will show:
1. **Simulation Start** - "🚀 SIMULATION STARTED - 5 games, Soccer - EPL"
2. **Game Start** - "⚽ NEW GAME: Barcelona @ Real Madrid"
3. **Agent Analysis** (one message per agent)
   - "🧠 Viktor (Sharp): Pass - no value"
   - "🤫 Nikolai (Insider): Barcelona moneyline @ 1.85, €45 stake, 85% confidence"
   - "🎲 Jozef (Degen): Barcelona moneyline @ 1.85, €98 stake, 95% confidence"
4. **Debate Phase** (agents discussing live)
   - "🗣️ Viktor: Line movement suggests..."
   - "🗣️ Jozef: Moon energy says..."
5. **Oracle Decision** (rich embed)
   - ⚽ Matchup: Barcelona @ Real Madrid
   - 🎯 Final Pick: Barcelona
   - 🗳️ Votes: Barcelona (4) vs Real Madrid (3)
   - 💰 Stake: €87.24
   - 📊 Odds: 1.85
   - 🔥 Confidence: 95%
   - 💭 Reasoning: (full reasoning shown)
6. **Simulation Complete** - "✅ SIMULATION COMPLETE - 5 games analyzed, €1,234.56 wagered"

### Current Status
- ✅ Test messages working
- ✅ Embed formatting working
- ✅ Oracle decision notifications working with votes & matchup
- ⏳ Agent analysis notifications ready to integrate
- ⏳ Debate phase notifications ready to integrate
- ⏳ Agent-by-agent real-time notifications in progress

## Files Modified

1. **notification/discord_notifier.py**
   - Added `format_sport_name()` utility
   - Updated `on_simulation_start()` to use formatted sport names
   - Updated `on_oracle_decision()` to include matchup, votes, full reasoning
   - Updated `on_debate_message()` to preserve full reasoning

2. **simulation/graph.py**
   - Added `asyncio` import
   - Modified `SyndicateState` to include `agent_votes` field
   - Updated `_oracle_decides()` to return vote breakdown tuple
   - Updated `_vote()` to capture vote data in state
   - Updated `analyze_game()` to return full state dict instead of just consensus bet
   - Updated `run_simulation()` to extract vote data and pass to Discord notifier

3. **main.py**
   - Added `DiscordNotifier` import
   - Added `asyncio` import
   - Initialize Discord notifier on startup
   - Send simulation start notification
   - Send simulation complete notification

## Testing

Run a quick test:
```bash
python main.py --games 2 --sample --no-live
```

Check your Discord channel for:
1. Simulation start message (with formatted sport name)
2. Two oracle decision embeds (with matchup, votes, full reasoning)
3. Simulation complete message
