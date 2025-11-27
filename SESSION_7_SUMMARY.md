# Session 7: Oracle Agent & Email Improvements

**Date**: Nov 26, 2025  
**Status**: ✅ Complete - Tested with real matches  
**Changes**: 3 major features implemented and tested

---

## What Changed

### 1. **Draw Odds Support** ✅
- Added `draw_odds: Optional[float]` to Game dataclass
- Created `_get_draw_odds()` method in OddsAPIClient
- Markets now show: `Home | Draw | Away` (3-way support)
- Email displays all three options

### 2. **Oracle Agent** ✅
Created `/agents/oracle_agent.py` - a real agent that:
- **Ingests all agent picks** and their reasoning
- **Analyzes consensus metrics**:
  - Average confidence per team
  - Total stake per team  
  - Which agent types are aligned
- **Calls LLM** to make informed decision based on all data
- **Falls back to voting** if LLM fails
- **Returns conviction level** (not just a bet)

The Oracle considers:
- Consensus and conviction levels across agent types
- Risk/reward vs market odds
- Any contrarian signals worth respecting
- Balance between sharps, insiders, degens, and bookies

### 3. **Voting vs Oracle Comparison** ✅
Both mechanisms run in parallel:

**Democratic Voting** (shows up in console and email):
```
📊 DEMOCRATIC VOTE: Arsenal (Arsenal: 4 votes, Bayern Munich: 6 votes)
   Pick: Bayern Munich by Tomáš
   Conviction: 70%
```

**Oracle Analysis**:
```
✅ ORACLE DECISION: Bet on Bayern Munich
   Reasoning: Sharp money reversing to Bayern. Line movement 2.22→3.43.
   Conviction: 70%
   (Agrees with democratic consensus)
```

**Or if they differ**:
```
⚠️ ORACLE DECISION: Bet on Slovan Bratislava
   Reasoning: Despite voting towards Vallecano, Slovan's home advantage...
   Conviction: 70%
   (Differs from vote winner: Rayo Vallecano)
```

### 4. **Email Layout Improvements** ✅

**Before**: Blob of text, compact, hard to read

**After**: Clean, scannable layout with:
- **Market Odds** section - Home | Draw | Away
- **Oracle's Choice** (blue highlight) - Shows Oracle's pick + conviction
- **Vote Breakdown** (small text) - Democratic vote for comparison
- **Why This Bet?** - Main consensus reasoning in highlighted box
- **All Agent Picks** - Readable bullet list of each agent's analysis

---

## Test Results

### Run: 3 real matches (Arsenal vs Bayern, Slovan vs Vallecano, Copenhagen vs Almaty)

**Console Output**:
```
✅ Elena (sharp): moneyline on Bayern Munich
   Stake: €4.88 | Confidence: 65%
   
✅ Nikolai (insider): moneyline on Arsenal FC
   Stake: €30.00 | Confidence: 75%
   
✅ Jozef (degen): moneyline on Arsenal FC
   Stake: €41.35 | Confidence: 95%
   
... (8 more agents)

🗳️  VOTING vs 🔮 ORACLE ANALYSIS
============================================================
📊 DEMOCRATIC VOTE: Bayern Munich (Arsenal: 4 votes, Bayern: 6 votes)
   Pick: Tomáš's bet (70% conviction)

✅ ORACLE DECISION: Bet on Bayern Munich
   Reasoning: Sharp money reversing. Line movement 2.22→3.43 significant.
   Conviction: 70%
   (Agrees with democratic consensus)

✅ BET PLACED: €16.00 on Bayern Munich
   Current Bankroll: €9984.00
```

**Email Output**: 
- Shows both votes AND oracle decision side-by-side
- Market odds with draw option
- Clear "Why This Bet?" section with consensus reasoning
- Agent picks as readable bullet points
- Easy to scan on mobile

---

## Key Improvements

### Before
```
<td colspan="5" style="padding: 10px; ... border-left: 3px solid #3498db;">
    <strong>All Agent Analysis:</strong><br>{all_agents}
</td>
```
→ Huge text blob, no separation, mobile-unfriendly

### After
```
<tr>
    <td colspan="5" style="... background-color: #f0f7ff;">
        <strong style="color: #2ecc71;">🔮 Oracle's Choice:</strong> {oracle_decision}<br>
        <strong style="color: #666; font-size: 11px;">📊 {voting_summary}</strong>
    </td>
</tr>
<tr>
    <td colspan="5" style="... background-color: #ffffff;">
        <strong>Why This Bet?</strong>
        <p style="... background-color: #f9f9f9; border-left: 3px solid #2ecc71;">{reasoning}</p>
    </td>
</tr>
<tr>
    <td colspan="5" style="... background-color: #f5f5f5;">
        <strong>🤖 All Agent Picks:</strong>
        <ul style="margin: 0; padding-left: 20px;">
            {agent_bullets}
        </ul>
    </td>
</tr>
```
→ Clean, scannable, mobile-friendly, easy to compare

---

## Files Modified

1. **agents/base_agent.py**
   - Added `draw_odds: Optional[float]` to Game dataclass

2. **agents/oracle_agent.py** (NEW)
   - Complete Oracle agent implementation
   - Analyzes all picks
   - Calls LLM for informed decision

3. **data/odds_api.py**
   - Added `_get_draw_odds()` method
   - Extracts 3-way odds from markets

4. **simulation/graph.py**
   - Added OracleAgent initialization
   - Updated `_vote()` to run both voting and Oracle in parallel
   - Shows comparison in console output
   - Passes both voting_summary and oracle_decision to email

5. **notification/email_sender.py**
   - Improved email layout with sections
   - Shows both voting and Oracle
   - Better formatting for mobile
   - Proper heading hierarchy

---

## Voting vs Oracle: When They Differ

The interesting part is when they **disagree**:

**Example: Slovan Bratislava vs Rayo Vallecano**

- **Democratic Vote**: Vallecano wins 3 votes (sharps + insiders favored favorites)
- **Oracle Decision**: Slovan wins (considers degen conviction, home form, market trap)

Console shows:
```
⚠️ ORACLE DECISION: Bet on Slovan Bratislava
   Reasoning: High conviction degens (95%), home advantage, public trap...
   (Differs from vote winner: Rayo Vallecano)
```

This is **good data** for testing:
- Did degens catch something sharps missed?
- Does Oracle's contrarian play work better?
- Which agent types are better predictors?

---

## Next Steps

1. **Test more matches** to see Oracle vs voting performance
2. **Add persistence** - track Oracle vs voting accuracy over time
3. **Dashboard** - visualize Oracle vs voting comparison
4. **Agent learning** - adjust agent weights based on past accuracy
5. **Docker** - production deployment setup

---

## Technical Notes

### Oracle Prompt
Oracle receives structured analysis of all picks:
```
Game: Arsenal @ Bayern Munich
AGENT PICKS SUMMARY:
Arsenal (4 agents):
  • Average Confidence: 75%
  • Total Stake: €101.35
  • Agents: Nikolai, Petra, Jozef, ...
  • Strongest: Jozef: "Arsenal at home..."

Bayern Munich (6 agents):
  • Average Confidence: 70%
  • Total Stake: €87.88
  • Agents: Elena, Boris, ...
  
Consider: Consensus, risk/reward, contrarian signals...
```

### Fallback Mechanism
If LLM fails or returns invalid JSON:
- Falls back to democratic voting
- Guarantees a decision is always made
- No risk of "no bet placed"

### Vote Tracking
Both voting counts and Oracle conviction stored in results:
```python
{
    "agent_votes": {"Arsenal": 4, "Bayern Munich": 6},  # voting
    "oracle_decision": "Oracle: Tomáš's bet on Bayern...",  # LLM decision
    "voting_summary": "Vote breakdown: Arsenal: 4, Bayern: 6",  # for email
}
```

---

## Email Section Breakdown

| Section | Purpose | Color | Info |
|---------|---------|-------|------|
| Market Odds | Show all available betting options | Light gray | Home/Draw/Away odds |
| Oracle's Choice | Highlight the actual pick | Blue (#f0f7ff) | Oracle decision + conviction |
| Vote Breakdown | Show democratic consensus | Small text | Vote counts for reference |
| Why This Bet? | Explain the reasoning | White | Consensus analysis |
| All Agent Picks | Show individual agent analysis | Light gray | Bulleted list per agent |

---

## Metrics to Track (Future)

For system improvement:
- Oracle vs Voting: Which makes better picks?
- Agent type accuracy: Sharps vs Insiders vs Degens vs Bookies
- Confidence calibration: Are 70% confident picks 70% likely to win?
- Oracle convergence: When does Oracle agree with vote?
- Line movement impact: Are reverse line movements accurate signals?

