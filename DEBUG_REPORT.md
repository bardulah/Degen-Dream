# Critical Issues Found - Debug Report

## Issue 1: Odds Inconsistency (CRITICAL)

### Problem
Two agents pick the same team but display wildly different odds. Example from latest run:
- Nikolai: Real Madrid moneyline "150" 
- Petra: Real Madrid moneyline "150"
- But displayed different odds values

### Root Cause
**The odds are being REGENERATED RANDOMLY for each agent call.**

In `agents/base_agent.py` line 127, the mock mode returns a random JSON response when API keys are missing:
```python
# When no real API key, returns random mock response
import random
should_bet = random.choice([True, False])
mock_response = {
    "odds": random.uniform(1.5, 2.5),  # RANDOM ODDS PER CALL!
    ...
}
```

But the real issue: **Each agent's `analyze_game()` call generates its own odds independently from the Game object's odds.**

The Game object has `home_odds` and `away_odds`, but agents aren't using these. They're either:
1. Generating their own odds via LLM
2. Using random mock data

### Solution Required
1. Pass Game.home_odds and Game.away_odds explicitly in the user_message
2. Agents should use these odds, not generate their own
3. All agent picks for the same team should show the SAME odds

---

## Issue 2: Stale Data in Agent Analysis (CRITICAL)

### Problem
Agents are NOT using real-time data (Gemini Search). They're making predictions based on old/stale data or hallucinating injuries.

Evidence from log:
- "a key Barcelona midfielder picked up a knock in training" (hallucinated, not verified)
- "fresh start for a HUGE WIN" (degen superstition, not real data)
- No reference to actual recent news/injuries/squad info

### Root Cause
**Gemini Search context is being passed but NOT INCLUDED IN AGENT PROMPTS**

In `simulation/graph.py` line 519-545:
```python
# Search context is fetched (lines 528-545)
search_context = search_client.get_match_context(...)
market_context.update(search_context)

# BUT in agents, they never reference this!
# Sharp agent line 42: market_context = context.get("market_data", "No additional market data")
# Insider agent line 43: nike_data = context.get("nike_data", "No Niké data available")

# The search_context keys don't match what agents look for!
```

### Solution Required
1. Standardize context keys (use consistent naming)
2. **Include search context in the user_message** to agents
3. Create a dedicated "real_time_data" section in prompts
4. Agents should cite sources from real data, not hallucinate

---

## Impact
1. **Odds Issue**: All picks appear to have random odds → impossible to verify bets → betting groups can't place actual bets
2. **Stale Data Issue**: Agents making picks on outdated info → predictions are unreliable → defeats purpose of Gemini Search integration

## Files to Fix
1. `agents/sharp_agent.py` - Include odds in prompt
2. `agents/insider_agent.py` - Include odds in prompt  
3. `agents/degen_agent.py` - Include odds in prompt
4. `agents/bookie_agent.py` - Include odds in prompt
5. `simulation/graph.py` - Pass search context properly to agents
6. All agent base prompts - Add "Use this real-time data for analysis" section

## Quick Fix Priority
1. **URGENT**: Fix odds inconsistency (5 min)
2. **URGENT**: Pass search context to agents (10 min)
3. **HIGH**: Update all agent prompts (15 min)
