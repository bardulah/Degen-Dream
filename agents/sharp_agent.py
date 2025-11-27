"""Sharp agent - analytical, value-focused betting."""

import json
from typing import Dict, Optional, Any
from .base_agent import BaseAgent, AgentType, Bet, Game


class SharpAgent(BaseAgent):
    """Sharp bettor focused on expected value and market efficiency."""

    def __init__(self, name: str, personality_prompt: str, initial_bankroll: float = 1000.0):
        """Initialize sharp agent."""
        super().__init__(name, AgentType.SHARP, personality_prompt, initial_bankroll)
        self.min_edge = 0.025  # Require 2.5% edge minimum
        self.clv_threshold = 0.02  # Closing line value threshold

    def analyze_game(self, game: Game, context: Dict[str, Any]) -> Optional[Bet]:
        """Analyze game using sharp betting principles.

        Args:
            game: Game to analyze
            context: Market data, line movements, etc.

        Returns:
            Bet if edge is found, None otherwise
        """
        # Build analysis prompt
        system_prompt = f"""You are {self.name}, a sharp professional sports bettor.

{self.personality_prompt}

Analyze games using:
1. Expected value calculation
2. Closing line value (CLV) prediction
3. Market efficiency analysis
4. Line shopping across books
5. Vig considerations

You ONLY bet when you identify a clear mathematical edge. Be extremely selective."""

        game_info = self._format_game_info(game)
        market_context = context.get("market_data", "No additional market data")
        pinnacle_odds = context.get("pinnacle_odds", "Not available")
        real_time_data = context.get("real_time_data", "")
        news_context = context.get("news_context", "")

        user_message = f"""Game Analysis Request:

{game_info}

REAL-TIME DATA (from web search):
{real_time_data}

{f"RECENT NEWS:{chr(10)}{news_context}" if news_context else ""}

Market Context:
{market_context}

Pinnacle Odds (sharpest book):
{pinnacle_odds}

Should we bet this game? If yes, provide:
1. Which bet (team/total)
2. Recommended line
3. Estimated edge (as decimal, e.g., 0.035 for 3.5%)
4. Confidence (0-1)
5. Reasoning (2-3 sentences citing data)

Respond in JSON format:
{{
    "should_bet": true/false,
    "bet_team": "team name or total",
    "bet_type": "moneyline/spread/total",
    "line": -110,
    "edge": 0.035,
    "confidence": 0.75,
    "reasoning": "Your analysis with data",
    "stake_percentage": 0.02
}}

If no bet, return {{"should_bet": false, "reasoning": "why not"}}"""

        response = self._call_claude(system_prompt, user_message)

        # Parse response
        try:
            analysis = self._parse_json_response(response)

            if not analysis.get("should_bet", False):
                return None

            # Validate edge requirement
            edge = analysis.get("edge", 0)
            if edge < self.min_edge:
                return None

            # Calculate stake (Kelly criterion variant)
            stake = self._calculate_stake(
                edge,
                analysis.get("confidence", 0.5),
                analysis.get("stake_percentage", 0.02)
            )

            # Get actual odds from the game based on the team bet
            bet_team = analysis["bet_team"]
            if analysis["bet_type"] == "moneyline":
                if bet_team.lower() == "draw":
                    odds = game.draw_odds if game.draw_odds else game.home_odds
                else:
                    odds = game.home_odds if bet_team == game.home_team else game.away_odds
            elif analysis["bet_type"] == "draw":
                odds = game.draw_odds if game.draw_odds else 1.0
                bet_team = "Draw"
            elif analysis["bet_type"] == "spread":
                odds = game.home_odds if bet_team == game.home_team else game.away_odds
            elif analysis["bet_type"] == "total":
                odds = game.over_odds if "Over" in bet_team else game.under_odds
                if not odds:
                    # Total odds not available, use moneyline as proxy
                    odds = game.home_odds
            else:
                odds = game.home_odds

            return Bet(
                game_id=game.id,
                team=analysis["bet_team"],
                bet_type=self.normalize_bet_type(analysis["bet_type"]),
                line=analysis["line"],
                odds=odds,
                stake=stake,
                confidence=analysis["confidence"],
                reasoning=analysis["reasoning"],
                agent_name=self.name
            )

        except Exception as e:
            print(f"Error analyzing game for {self.name}: {e}")
            return None

    def _format_game_info(self, game: Game) -> str:
        """Format game information for analysis."""
        info = f"""Game: {game.away_team} @ {game.home_team}
Sport: {game.sport}
Time: {game.commence_time}
Bookmaker: {game.bookmaker}

Moneyline:
- {game.home_team}: {game.home_odds}
- {game.away_team}: {game.away_odds}
"""
        # Add draw odds if available (for soccer)
        if game.draw_odds:
            info += f"- Draw: {game.draw_odds}\n"
        
        if game.home_spread:
            info += f"""\nSpread:
- {game.home_team}: {game.home_spread} ({game.home_odds})
- {game.away_team}: {game.away_spread} ({game.away_odds})
"""
        if game.over_under:
            info += f"""\nTotal: {game.over_under}
- Over: {game.over_odds}
- Under: {game.under_odds}
"""
        return info

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from Claude response."""
        # Try to extract JSON from markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        return json.loads(response)

    def _calculate_stake(self, edge: float, confidence: float, base_percentage: float) -> float:
        """Calculate bet stake using fractional Kelly.

        Args:
            edge: Estimated edge
            confidence: Confidence in analysis
            base_percentage: Base stake percentage

        Returns:
            Stake amount
        """
        # Fractional Kelly: fraction * edge * bankroll
        kelly_fraction = 0.25  # Conservative quarter-Kelly
        adjusted_edge = edge * confidence  # Adjust for confidence
        stake_percentage = min(kelly_fraction * adjusted_edge, base_percentage)

        return self.bankroll * stake_percentage

    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
