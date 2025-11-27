"""Oracle agent - analyzes all agent picks and makes final decision."""

import json
from typing import List, Dict, Any, Optional
from agents.base_agent import BaseAgent, AgentType, Bet, Game
from config.settings import settings


class OracleAgent(BaseAgent):
    """Oracle agent that ingests all agent opinions and decides the pick."""

    def __init__(self):
        """Initialize Oracle agent."""
        personality_prompt = """You are the Oracle - the wise keeper of the syndicate. Your role is to:

1. Analyze all agent picks and their reasoning
2. Identify patterns and consensus
3. Evaluate confidence levels and conviction
4. Consider market context and risk/reward
5. Make a final decision on which bet to place

You should:
- Favor bets with high agreement across agent types
- Value strong confidence signals from sharps and insiders
- Respect contrarian views if well-reasoned
- Consider Kelly Criterion principles
- Balance risk and expected value

Respond in JSON format:
{
    "team": "team_name",
    "reasoning": "Why this pick over others",
    "conviction": 0.85,
    "risk_assessment": "low/medium/high"
}"""
        
        super().__init__(
            name="Oracle",
            agent_type=AgentType.SHARP,
            personality_prompt=personality_prompt,
            initial_bankroll=0  # Oracle doesn't have its own bankroll
        )
    
    def analyze_picks(
        self,
        game: Game,
        all_bets: List[Bet],
        context: Dict[str, Any] = None
    ) -> Optional[Bet]:
        """Analyze all agent picks and decide the best bet.
        
        Args:
            game: The game being analyzed
            all_bets: All bets proposed by agents
            context: Market context
        
        Returns:
            Oracle's final bet decision
        """
        if not all_bets:
            return None
        
        # Build agent pick summary
        picks_by_team = {}
        for bet in all_bets:
            team = bet.team
            if team not in picks_by_team:
                picks_by_team[team] = []
            picks_by_team[team].append({
                "agent": bet.agent_name,
                "confidence": bet.confidence,
                "stake": bet.stake,
                "odds": bet.odds,
                "reasoning": bet.reasoning
            })
        
        # Build analysis prompt
        analysis_prompt = f"""Game: {game.away_team} @ {game.home_team}
Sport: {game.sport}
Market Odds: Home {game.home_odds} | Draw {getattr(game, 'draw_odds', 'N/A')} | Away {game.away_odds}

AGENT PICKS SUMMARY:
"""
        
        for team, picks in picks_by_team.items():
            analysis_prompt += f"\n{team} ({len(picks)} agents):\n"
            avg_confidence = sum(p['confidence'] for p in picks) / len(picks)
            total_stake = sum(p['stake'] for p in picks)
            
            analysis_prompt += f"  • Average Confidence: {avg_confidence:.0%}\n"
            analysis_prompt += f"  • Total Stake: €{total_stake:.2f}\n"
            analysis_prompt += f"  • Agents: {', '.join([p['agent'] for p in picks])}\n"
            
            # Show reasoning from strongest conviction agents
            strongest = sorted(picks, key=lambda x: x['confidence'], reverse=True)[:2]
            for pick in strongest:
                analysis_prompt += f"    - {pick['agent']}: {pick['reasoning'][:100]}...\n"
        
        if context and context.get('real_time_data'):
            analysis_prompt += f"\nREAL-TIME CONTEXT:\n{context['real_time_data']}\n"
        
        analysis_prompt += "\nWhich team should the Oracle bet on? Consider:\n"
        analysis_prompt += "1. Consensus and conviction levels\n"
        analysis_prompt += "2. Balance of agent types (sharps, insiders, degens, bookies)\n"
        analysis_prompt += "3. Risk/reward and odds value\n"
        analysis_prompt += "4. Any contrarian signals worth respecting\n"
        
        # Call LLM to get Oracle's decision
        try:
            response = self._call_llm(analysis_prompt)
            
            # Parse response
            try:
                # Try to extract JSON from response
                if "{" in response and "}" in response:
                    json_str = response[response.find("{"):response.rfind("}")+1]
                    decision = json.loads(json_str)
                else:
                    decision = json.loads(response)
                
                chosen_team = decision.get("team")
                oracle_reasoning = decision.get("reasoning", "Syndicate consensus")
                conviction = decision.get("conviction", 0.75)
                
            except json.JSONDecodeError:
                # Fallback: pick team with most votes
                chosen_team = max(picks_by_team.keys(), 
                                key=lambda t: len(picks_by_team[t]))
                oracle_reasoning = f"Oracle consensus on {chosen_team}"
                conviction = 0.65
            
            # Find best bet for chosen team
            team_bets = [b for b in all_bets if b.team == chosen_team]
            if not team_bets:
                # If chosen team has no bets, pick team with most consensus
                chosen_team = max(picks_by_team.keys(), 
                                 key=lambda t: len(picks_by_team[t]))
                team_bets = [b for b in all_bets if b.team == chosen_team]
            
            if team_bets:
                # Pick strongest conviction bet from chosen team
                oracle_bet = max(team_bets, 
                               key=lambda b: b.stake + b.confidence)
                
                # Create Oracle's bet with enhanced reasoning
                oracle_bet_copy = Bet(
                    game_id=oracle_bet.game_id,
                    team=chosen_team,
                    bet_type=oracle_bet.bet_type,
                    line=oracle_bet.line,
                    odds=oracle_bet.odds,
                    stake=oracle_bet.stake,
                    confidence=conviction,
                    reasoning=oracle_reasoning,
                    agent_name="Oracle"
                )
                
                return oracle_bet_copy
            
            return None
        
        except Exception as e:
            print(f"Oracle analysis error: {e}")
            # Fallback to voting mechanism
            return self._oracle_fallback_vote(all_bets)
    
    def _oracle_fallback_vote(self, all_bets: List[Bet]) -> Optional[Bet]:
        """Fallback voting mechanism if LLM fails."""
        # Count votes by team
        team_votes = {}
        team_bets = {}
        
        for bet in all_bets:
            team = bet.team
            if team not in team_votes:
                team_votes[team] = 0
                team_bets[team] = []
            
            team_votes[team] += 1
            team_bets[team].append(bet)
        
        # Find winning team
        winning_team = max(team_votes, key=team_votes.get)
        winning_bets = team_bets[winning_team]
        
        # Pick strongest conviction from winning team
        best_bet = max(winning_bets, key=lambda b: b.stake + b.confidence)
        
        return Bet(
            game_id=best_bet.game_id,
            team=best_bet.team,
            bet_type=best_bet.bet_type,
            line=best_bet.line,
            odds=best_bet.odds,
            stake=best_bet.stake,
            confidence=0.70,
            reasoning="Oracle consensus vote",
            agent_name="Oracle"
        )
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        if self.provider == "openrouter":
            message = self.client.chat.completions.create(
                model="google/gemini-2.0-flash-exp:free",
                messages=[
                    {"role": "system", "content": self.personality_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return message.choices[0].message.content
        
        elif self.provider == "anthropic":
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                system=self.personality_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        
        elif self.provider == "gemini":
            import google.generativeai as genai
            full_prompt = f"{self.personality_prompt}\n\n{prompt}"
            response = self.model.generate_content(full_prompt)
            return response.text
        
        elif self.provider == "groq":
            message = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": self.personality_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return message.choices[0].message.content
        
        else:
            # Fallback
            return "Unable to process"
