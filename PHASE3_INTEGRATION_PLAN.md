# Phase 3: Integration Plan
**Objective**: Integrate async processing, agent learning, and event streaming into the main simulation loop  
**Estimated Duration**: 4-6 hours  
**Priority**: HIGH - Unlocks 3-4x performance improvement

---

## 📋 Integration Checklist

### 1. Integrate Async Agent Analysis [CRITICAL]
**File**: `simulation/graph.py`  
**Task**: Replace sequential agent analysis with parallel processing  

**Current Code** (lines ~360-420):
```python
# Sequential: 10 agents * 2 seconds each = 20 seconds
for agent in agents:
    bet = agent.analyze_game(game, context)
    agent_bets.append(bet)
```

**Target Code**:
```python
# Parallel: ~2 seconds total
from simulation.async_simulation import run_async_simulation

agent_bets = run_async_simulation(
    agents=syndicate.agents,
    game=game,
    context=context,
    max_workers=5
)
```

**Benefits**:
- ✅ 3-4x faster per game (20s → 5-6s)
- ✅ Better CPU utilization
- ✅ Seamless fallback to sequential on error

**Testing**:
```bash
python main.py --games=10 --sample --no-live
# Should complete in ~1 minute (vs 3 minutes)
```

---

### 2. Integrate Agent Learning [HIGH]
**File**: `simulation/graph.py`  
**Task**: Apply confidence weighting based on agent history  

**Location**: In `_settle_bets()` method, before bet settlement

**Implementation**:
```python
from simulation.agent_learning import AgentLearningSystem, ConfidenceAdjustmentFilter

# Initialize once per simulation
learning_system = AgentLearningSystem(db=db)
adjustment_filter = ConfidenceAdjustmentFilter(learning_system)

# For each bet placed:
def place_bet(agent_name, bet_confidence, bet_amount):
    # Adjust confidence based on history
    adjusted_confidence = adjustment_filter.adjust_bet_confidence(
        agent_name=agent_name,
        bet_confidence=bet_confidence
    )
    
    # Only place if meets threshold
    if not adjustment_filter.should_accept_bet(
        agent_name=agent_name,
        bet_confidence=bet_confidence,
        min_threshold=0.55
    ):
        return None  # Skip this bet
    
    # Place with adjusted confidence
    return {
        "agent": agent_name,
        "original_confidence": bet_confidence,
        "adjusted_confidence": adjusted_confidence,
        "amount": bet_amount
    }
```

**After Simulation**:
```python
# Update learning system with results
for agent in agents:
    agent_bets = [b for b in bets if b["agent"] == agent.name]
    learning_system.update_agent_stats(
        agent_name=agent.name,
        simulation_id=simulation_id,
        bets=agent_bets
    )
```

**Benefits**:
- ✅ Overconfident agents dampened
- ✅ Underconfident agents boosted
- ✅ Better bet selection over time

---

### 3. Emit Events for Real-Time UI Updates [MEDIUM]
**File**: `simulation/graph.py`  
**Task**: Emit events for Streamlit live updates  

**Integration Points**:

```python
from simulation.event_emitter import event_emitter, SimulationEventType

# At game start
event_emitter.emit(
    SimulationEventType.GAME_START,
    game_number=game_idx,
    data={"team1": game.team1, "team2": game.team2}
)

# During agent analysis
event_emitter.emit(
    SimulationEventType.AGENT_ANALYSIS,
    game_number=game_idx,
    data={
        "agent": agent.name,
        "decision": bet.type if bet else "PASS",
        "confidence": bet.confidence if bet else None,
        "stake": bet.amount if bet else None
    }
)

# During debate
event_emitter.emit(
    SimulationEventType.DEBATE_START,
    game_number=game_idx,
    data={}
)

for speaker, statement in debate_results.items():
    event_emitter.emit(
        SimulationEventType.DEBATE_STATEMENT,
        game_number=game_idx,
        data={"speaker": speaker, "statement": statement}
    )

# On consensus bet
event_emitter.emit(
    SimulationEventType.CONSENSUS_BET,
    game_number=game_idx,
    data={
        "type": consensus_bet.type,
        "stake": consensus_bet.amount,
        "confidence": consensus_bet.confidence
    }
)

# On bet result
event_emitter.emit(
    SimulationEventType.BET_RESULT,
    game_number=game_idx,
    data={
        "result": "win" if won else "loss",
        "amount": pnl,
        "bankroll": current_bankroll,
        "roi": roi,
        "win_rate": win_rate
    }
)

# At game end
event_emitter.emit(
    SimulationEventType.GAME_END,
    game_number=game_idx,
    data={...}
)

# At simulation end
event_emitter.emit(
    SimulationEventType.SIMULATION_COMPLETE,
    game_number=num_games,
    data={...}
)
```

**Streamlit Listener** (in `gui/streamlit_app.py`):
```python
def on_bet_result(event):
    """Update UI on bet result."""
    progress_bar.update(event.data.get('result') == 'win')
    ticker.update(
        event.data.get('bankroll'),
        event.game_number,
        event.data.get('roi'),
        event.data.get('win_rate')
    )
    # Trigger Streamlit rerun
    st.rerun()

event_emitter.on(SimulationEventType.BET_RESULT, on_bet_result)
```

**Benefits**:
- ✅ Real-time progress feedback
- ✅ No need to wait for simulation to complete
- ✅ Better UX for long simulations

---

### 4. Enhance Debate Logic [MEDIUM] - #15
**File**: `simulation/graph.py`  
**Task**: Implement weighted voting and persuasion scoring  

**Current**: Simple majority voting  
**Target**: Weight votes by agent ROI + persuasion scoring

**Implementation**:
```python
def run_debate_with_weighted_voting(agents, game, agent_bets):
    """Run debate with weighted voting based on agent quality."""
    from simulation.agent_learning import AgentLearningSystem
    
    learning_system = AgentLearningSystem(db=db)
    agent_stats = learning_system.get_all_agent_stats()
    
    # Calculate agent weights based on ROI
    weights = {}
    for agent in agents:
        stats = agent_stats.get(agent.name)
        roi = stats.roi if stats else 0.0
        # Normalize: average ROI = 1.0
        weights[agent.name] = 1.0 + (roi / 100.0)
    
    # Run debate
    debate_statements = {}
    for agent in agents:
        statement = agent.debate({"game": game, "bets": agent_bets}, agents)
        debate_statements[agent.name] = {
            "statement": statement,
            "weight": weights[agent.name],
            "persuasion_score": calculate_persuasion(statement)
        }
    
    # Weighted voting
    best_bet = None
    best_score = 0
    for agent_name, data in debate_statements.items():
        vote_score = data["weight"] * data["persuasion_score"]
        if vote_score > best_score:
            best_score = vote_score
            best_bet = find_agent_bet(agent_name, agent_bets)
    
    return best_bet

def calculate_persuasion(statement: str) -> float:
    """Score statement for persuasiveness (1.0 = neutral)."""
    # Simple heuristics:
    # - Longer, more detailed statements = higher persuasion
    # - Quantitative claims = higher persuasion
    # - Logical connectors (therefore, thus) = higher persuasion
    
    persuasion = 1.0
    persuasion += len(statement.split()) / 100  # Length bonus
    persuasion += statement.count("therefore") * 0.2
    persuasion += statement.count("because") * 0.2
    
    return min(2.0, persuasion)  # Cap at 2.0
```

**Benefits**:
- ✅ Better agents have more influence
- ✅ More nuanced betting decisions
- ✅ Debate becomes more meaningful

---

## 🔄 Integration Order (Recommended)

### Phase 3.1: Async Integration (4 hours)
1. Update `_create_default_agents()` location check
2. Modify agent analysis loop in `run_simulation()`
3. Add async import and initialization
4. Test with `--games=5`
5. Benchmark performance improvement

### Phase 3.2: Agent Learning (3 hours)
1. Initialize `AgentLearningSystem` at simulation start
2. Apply confidence adjustment in `_place_consensus_bet()`
3. Update agent stats after each simulation
4. Test with 2 simulations (verify learning)
5. Visualize learned weights

### Phase 3.3: Event Streaming (2 hours)
1. Add event emissions throughout loop
2. Connect Streamlit listeners
3. Test live update UI
4. Verify no performance regression

### Phase 3.4: Debate Enhancement (2 hours)
1. Implement weighted voting
2. Add persuasion scoring
3. Test debate quality improvements
4. Compare vs. simple majority

---

## 📊 Expected Performance Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|------------|
| Time per 100-game sim | 30 minutes | 8-10 minutes | **3-4x faster** |
| Agent analysis time | 20 seconds | 5 seconds | **4x faster** |
| Learning curve | Linear | Exponential | **Better long-term** |
| User experience | Waiting... | Live updates | **Much better** |

---

## ✅ Success Criteria

- [ ] Async agent analysis working (verified with benchmark)
- [ ] Agent learning system integrated (confidence weights applied)
- [ ] Events being emitted during simulation
- [ ] Streamlit UI updates in real-time
- [ ] All tests passing
- [ ] Performance benchmarks show 3-4x improvement
- [ ] No regression in simulation accuracy

---

## 🚀 Files to Modify

| File | Changes | Lines | Difficulty |
|------|---------|-------|------------|
| `simulation/graph.py` | Core integration (4 sections) | ~100 | HIGH |
| `gui/streamlit_app.py` | Event listener setup | ~30 | LOW |
| `main.py` | CLI event listener (optional) | ~20 | LOW |

---

## 🔗 Related Files

**Creating**:
- None

**Using**:
- `simulation/async_simulation.py` ✅
- `simulation/agent_learning.py` ✅
- `simulation/event_emitter.py` ✅

**Updated**:
- `simulation/graph.py`
- `gui/streamlit_app.py`

---

## 📝 Notes

- Use `run_async_simulation()` wrapper (blocks and handles cleanup)
- Agent learning needs at least 10 bets per agent to be effective
- Events are non-blocking; simulation continues even if listener fails
- Consider adding `logging` calls alongside events for debugging

---

**Ready to start Phase 3? The foundation is solid. Integration should be straightforward.**
