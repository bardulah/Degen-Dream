# Architecture: Session 8 Data Flow

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT COMPOSITION                          │
│  (3 Sharps, 2 Insiders, 3 Degens, 2 Bookies)                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   LEAGUE SELECTOR                               │
│  Scores 10+ leagues based on agent type preferences             │
│  • Sharps → Liquidity, Stability, Efficiency                    │
│  • Insiders → Injury Info, Volume, Liquidity                    │
│  • Degens → Volume, Chaos (volatility), Liquidity               │
│  • Bookies → Volume, Inefficiency, Liquidity                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
         ┌──────────────────────────────────────┐
         │   SELECTED LEAGUES (8 recommended)   │
         │  Soccer (5) + Basketball (1) +       │
         │  Hockey (1) + Tennis (1)             │
         └──────────────────────────────────────┘
                            ↓
         ┌──────────────────────────────────────┐
         │   DAILY ODDS FETCHER ORCHESTRATION   │
         └──────────────────────────────────────┘
              ↓                              ↓
    ┌─────────────────────┐      ┌─────────────────────┐
    │  Nike.sk Scraper    │      │  OddsAPI Client V2  │
    │  (Soccer, European) │      │  (Multi-Sport)      │
    │                     │      │                     │
    │  • Playwright       │      │  • Retry Logic      │
    │  • Headless Browser │      │  • Exponential      │
    │  • 49 games/day     │      │    Backoff          │
    │  • 100% Success     │      │  • 30-min Cache     │
    │    (usually)        │      │  • Health Tracking  │
    └─────────────────────┘      │  • Error Handler    │
            ↓                      └─────────────────────┘
    ┌─────────────────────┐              ↓
    │ Soccer Odds         │      ┌────────────────────┐
    │ (Team A vs Team B)  │      │ OddsAPI Requests   │
    │ • Home: 2.5         │      │                    │
    │ • Away: 2.8         │      │ League 1 (retry 0) │
    │ • Draw: 3.2         │      │  ↓ Success → Cache │
    │                     │      │                    │
    │ (49 games)          │      │ League 2 (retry 0) │
    │                     │      │  ↓ 401 → Retry 1  │
    └─────────────────────┘      │  ↓ 429 → Backoff  │
            ↓                      │  ↓ Timeout → Retry 2
            └──────────┬───────────→ League 3...     │
                       │            └────────────────┘
                       ↓                    ↓
        ┌──────────────────────────────────────────┐
        │  MERGE & DEDUPLICATE                     │
        │  (Keep best odds across sources)         │
        │  • Arsenal vs Man City (Nike vs DK)      │
        │  • Keep highest home odds (DK)           │
        │  • Mark source for tracking              │
        └──────────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────┐
        │  UNIFIED GAME POOL (50-80 games)         │
        │  Grouped by Sport:                       │
        │  • Soccer: 49 games (Nike.sk)            │
        │  • Basketball: 6 games (OddsAPI/NBA)     │
        │  • Hockey: 4 games (OddsAPI/NHL)         │
        │  • Tennis: 3 games (OddsAPI/ATP)         │
        └──────────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────┐
        │  SYNDICATE GRAPH (graph.py)              │
        │  • 10 Agents analyze games               │
        │  • Debate phase (first 5 agents)         │
        │  • Oracle decides (analyzes all picks)   │
        │  • Voting shows consensus (transparent)  │
        └──────────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────┐
        │  RESULTS (Per Game)                      │
        │  • Consensus bet (Oracle or vote)        │
        │  • All agent picks (for reference)       │
        │  • Reasoning from all agents             │
        │  • Odds and stake                        │
        │  • Status: PENDING (waiting for results) │
        └──────────────────────────────────────────┘
                       ↓
        ┌──────────────────────────────────────────┐
        │  STORAGE & NOTIFICATIONS                 │
        │  • Database (PENDING bets)               │
        │  • Email report (HTML, full reasoning)   │
        │  • Discord webhook (live updates)        │
        │  • Console logging (detailed output)     │
        └──────────────────────────────────────────┘
```

---

## LeagueSelector Deep Dive

### Configuration Hierarchy

```
League Tiers (top.py)
│
├─ Tier 1: High Quality (6 leagues)
│  ├─ EPL (soccer)          5/5 liquidity, 5/5 stability, 5/5 efficiency
│  ├─ La Liga (soccer)      5/5 liquidity, 4/5 stability, 5/5 efficiency
│  ├─ Bundesliga (soccer)   5/5 liquidity, 4/5 stability, 4/5 efficiency
│  ├─ Serie A (soccer)      5/5 liquidity, 4/5 stability, 4/5 efficiency
│  ├─ Ligue 1 (soccer)      4/5 liquidity, 3/5 stability, 4/5 efficiency
│  └─ NBA (basketball)      5/5 liquidity, 3/5 stability, 4/5 efficiency
│
├─ Tier 2: Balanced (4 leagues)
│  ├─ EuroLeague (basketball)  3/5 liquidity, 3/5 stability, 3/5 efficiency
│  ├─ NHL (hockey)             4/5 liquidity, 4/5 stability, 4/5 efficiency
│  ├─ ATP (tennis)             3/5 liquidity, 2/5 stability, 3/5 efficiency
│  └─ WTA (tennis)             2/5 liquidity, 2/5 stability, 2/5 efficiency
│
└─ Tier 3: Niche (2+ leagues)
   ├─ Dutch Eredivisie (soccer) 3/5 liquidity, 2/5 stability, 2/5 efficiency
   └─ Portuguese Primeira (soccer) 2/5 liquidity, 2/5 stability, 2/5 efficiency
```

### Scoring Algorithm

```python
# For each agent type, score = weighted combination of league traits

sharp_score = (
    liquidity * 0.5 +           # 50% importance
    line_stability * 0.3 +      # 30% importance
    market_efficiency * 0.2     # 20% importance
) * 20  # Scale to 0-100

# Bonus if league is in agent's preferred list
if league in best_for_agent:
    score *= 1.2  # 20% bonus

# Result: 0-100 score per agent-league combination
```

### Example: NBA Scoring

```
NBA Metrics:
  • Liquidity: 5/5          (all bookmakers offer it)
  • Public Volume: 5/5      (most bet sport in US)
  • Injury Info: 5/5        (extensive coverage)
  • Line Stability: 3/5     (moves due to public money)
  • Market Efficiency: 4/5  (fairly efficient)

Scores (before bonus):
  Sharp: (5*0.5 + 3*0.3 + 4*0.2) * 20 = 92
  Insider: (5*0.3 + 5*0.3 + 5*0.4) * 20 = 100
  Degen: (5*0.4 + (6-3)*0.3 + 5*0.3) * 20 = 100  (chaos bonus)
  Bookie: (5*0.5 + (6-4)*0.3 + 5*0.2) * 20 = 98

Final (with bonus for all agents):
  Sharp: 92 × 1.2 = 100 (capped)
  Insider: 100 × 1.2 = 100 (capped)
  Degen: 100 × 1.2 = 100 (capped)
  Bookie: 98 × 1.2 = 100 (capped)
```

---

## OddsAPIClientV2 Error Handling Flow

```
Request to League
        ↓
   ┌────────────────┐
   │ Try Request    │
   │ (10s timeout)  │
   └────────────────┘
        ↓
   ┌────────────────────────────────────────┐
   │ Response Status?                       │
   └────────────────────────────────────────┘
   ↓                ↓              ↓          ↓
  200             401            404         429
 (OK)          (Invalid Key)  (Sport Not    (Rate
              Found)          Limited)
   ↓                ↓              ↓          ↓
 Parse          Log Once,       Skip       Exponential
  Odds          Skip League     League      Backoff
   ↓                ↓              ↓          ↓
 Cache           Move Next      Move Next   Wait 1s
 (30 min)        League          League     Retry
   ↓                ↓              ↓          ↓
 Return          (no retry)     (no retry)  [Retry 2]
 Games                                       Wait 2s
                                            Retry
                                             ↓
                                           [Retry 3]
                                            Wait 4s
                                            Retry
                                             ↓
                                            Fail
                                        +error
                                        counter++
```

### Health Monitoring

```
Consecutive Errors Counter
        ↓
    Count < 3?
    ↙       ↖
  Yes       No
   ↓         ↓
Continue  API Healthy = False
 Normal   Enter Backoff (60s)
          ↓
      Use Nike.sk Only
      ↓
      After 60s, Reset Counter
      Try OddsAPI Again
```

---

## Caching Strategy

```
Request Arsenal vs Man City odds at 2:00pm
        ↓
    League in cache? → No
        ↓
    Make API call (OddsAPI)
        ↓
    Store in cache with timestamp (2:00:00pm)
        ↓
    Return results
        ↓
Request same league at 2:15pm
        ↓
    League in cache? → Yes
        ↓
    Check age: 15 minutes < 30 min TTL → Valid
        ↓
    Return cached results (no API call)
        ↓
Request same league at 2:35pm
        ↓
    League in cache? → Yes
        ↓
    Check age: 35 minutes > 30 min TTL → Expired
        ↓
    Delete from cache
        ↓
    Make new API call (cache miss)
        ↓
    Store new results, return
```

---

## Daily Workflow Example

### 10:00 AM User runs `main.py --daily --games 5`

```
10:00:00 → Agent Composition detected: 3 Sharps, 2 Insiders, 3 Degens, 2 Bookies
10:00:01 → LeagueSelector recommends: EPL, La Liga, NBA, Serie A, etc. (8 leagues)
10:00:02 → DailyOddsFetcher starts

          ├─ Nike.sk: Send request
          │  └─ (5 seconds loading)
          │  └─ ✅ 49 soccer games fetched + cached
          │
          └─ OddsAPI: Start parallel requests
             ├─ EPL request
             │  └─ 200 OK → 10 games fetched + cached 30 min
             ├─ La Liga request
             │  └─ 401 Unauthorized → Retry in 1s
             │  └─ Still failing → Try again in 2s
             │  └─ 200 OK → 8 games fetched + cached
             ├─ NBA request
             │  └─ 200 OK → 6 games fetched + cached
             └─ ... (more leagues)

10:00:30 → OddsAPI health check: 11/12 requests successful (91.7% success rate)
10:00:31 → Merge Nike.sk (49) + OddsAPI (28) = 77 games total

10:00:32 → Start analysis:
           ├─ Game 1: Arsenal vs Bayern
           │  ├─ Agent 1 (Sharp): EV analysis → Recommend Bayern
           │  ├─ Agent 2 (Insider): Injury news → Recommend Arsenal
           │  ├─ Agent 3 (Degen): Superstition → Recommend Over
           │  ├─ ... (7 more agents)
           │  └─ Oracle: Analyzes all picks → Decide: Bayern 70% conviction
           │
           ├─ Game 2: Lakers vs Warriors
           │  └─ (same process)
           │
           └─ ... (3 more games)

10:02:00 → Simulation complete, save results to database
           ├─ 5 games analyzed
           ├─ 50 individual agent picks
           ├─ 5 consensus bets (Oracle decisions)
           ├─ All stored as PENDING (awaiting real results)
           └─ Status: Ready for settlement

10:02:30 → Email report sent
           ├─ Each game: Odds, Oracle's choice, vote breakdown, reasoning
           ├─ All picks included
           └─ Status: PENDING RESULTS

10:03:00 → Discord notification
           ├─ Oracle decisions posted
           ├─ Agent debate summary
           └─ Awaiting game results
```

---

## Data Model

### Input (LeagueConfig)

```python
@dataclass
class LeagueConfig:
    key: str                        # API key: "soccer_epl"
    sport: str                      # "soccer"
    name: str                       # "English Premier League"
    region: str                     # "eu"
    liquidity: int                  # 1-5
    public_volume: int              # 1-5
    injury_info: int                # 1-5
    line_stability: int             # 1-5
    market_efficiency: int          # 1-5
    best_for: List[AgentProfile]    # [SHARP, BOOKIE]
```

### Processing (Game)

```python
@dataclass
class Game:
    id: str
    home_team: str
    away_team: str
    sport: str                      # "soccer", "basketball", etc.
    commence_time: str              # ISO timestamp
    bookmaker: str                  # "nike_sk", "draftkings", etc.
    home_odds: float                # 2.5
    away_odds: float                # 2.8
    draw_odds: Optional[float]      # 3.2 (3-way market)
    home_spread: Optional[float]
    away_spread: Optional[float]
    over_under: Optional[float]
    over_odds: Optional[float]
    under_odds: Optional[float]
```

### Output (Bet)

```python
@dataclass
class Bet:
    game_id: str
    team: str                       # Winning team per Oracle
    bet_type: str                   # "moneyline", "spread", "total"
    line: float
    odds: float
    stake: float
    confidence: float               # 0-1 (Oracle's conviction)
    reasoning: str                  # Full explanation
    agent_name: str                 # "Oracle" (or fallback to vote winner)
```

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| **LeagueSelector.recommend()** | 10ms | 10 leagues, scoring only |
| **Nike.sk scrape** | 5-10s | Parallel browser automation |
| **OddsAPI request** | 1-2s | Per league, with retries |
| **Cache hit** | <1ms | In-memory lookup |
| **Cache miss + retry** | 6-8s | 1s + 2s backoff |
| **Merge/dedup** | <100ms | 50-80 games |
| **Total fetch time** | 10-15s | Nike + OddsAPI in parallel |

---

## Backward Compatibility

**No Breaking Changes:**

✅ Game model: Added `draw_odds` (optional field, Session 7)  
✅ Agent interface: Unchanged  
✅ Graph.py: Unchanged (works with new data sources)  
✅ Email format: Unchanged  
✅ Database schema: Unchanged  
✅ Oracle agent: Works with all sources  
✅ Old OddsAPIClient: Aliased to OddsAPIClientV2  

---

## Scaling Notes

**Current Setup:**
- Nike.sk: 49 games/day (fixed, peak 2-4pm)
- OddsAPI: 20-30 games/day (varies by API availability)
- Total: 50-80 games/day across 4 sports

**To Scale to 100+ games:**
1. Add more soccer leagues (Danish Superliga, Turkish Super Lig, etc.)
2. Add more basketball leagues (EuroLeague, CBA)
3. Add more sports (cricket, rugby, Formula 1)
4. Implement persistent cache (disk, not memory)
5. Add rate limiting to protect own APIs

**API Rate Limits:**
- Nike.sk: No limit (browser scraping, but slow)
- OddsAPI: ~100 requests/month on free tier
  - Current usage: ~20 requests/day = ~600/month
  - Need: Paid tier or fallback strategy

---

**Architecture Status**: ✅ Ready for production  
**Next Phase**: Results Matching (Flashscore, bet settlement)
