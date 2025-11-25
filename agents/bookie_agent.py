"""Bookie agent - manipulates lines and predicts public betting patterns."""

import json
from typing import Dict, Optional, Any, List
from .base_agent import BaseAgent, AgentType, Bet, Game


class BookieAgent(BaseAgent):
    """Bookie who manipulates lines and analyzes public betting patterns."""

    def __init__(self, name: str, personality_prompt: str, initial_bankroll: float = 1000.0):
        """Initialize bookie agent."""
        super().__init__(name, AgentType.BOOKIE, personality_prompt, initial_bankroll)
        self.juice = 0.10  # Standard vig
        self.public_fade_threshold = 0.70  # Fade public if >70% on one side

    def analyze_game(self, game: Game, context: Dict[str, Any]) -> Optional[Bet]:
        """Analyze game from bookmaker perspective - fade the public.

        Args:
            game: Game to analyze
            context: Public betting percentages, line movements

        Returns:
            Bet that fades public money, None if balanced
        """
        system_prompt = f"""You are {self.name}, a bookmaker in the Bratislava Betting Syndicate.

{self.personality_prompt}

As a bookie, you:
1. Set lines to balance action (but profit from juice)
2. Identify where public money flows
3. Shade lines to trap square bettors
4. Fade heavy public sides
5. Predict line movements
6. Know when sharps are on one side

Your edge comes from understanding PUBLIC vs SHARP money and exploiting it."""

        game_info = self._format_game_info(game)
        public_data = context.get("public_betting", "No public betting data")
        line_movements = context.get("line_movements", "No line movement data")

        user_message = f"""Game to set lines for:

{game_info}

Public Betting Percentages:
{public_data}

Line Movements:
{line_movements}

Analysis questions:
1. Where is public money going?
2. Is sharp money on the other side (reverse line movement)?
3. Should we fade the public or respect sharp action?
4. What's the trap play?

Respond in JSON:
{{
    "public_side": "home/away/over/under",
    "public_percentage": 75,
    "sharp_side": "opposite or same",
    "should_bet": true/false,
    "bet_team": "team to bet",
    "bet_type": "moneyline/spread/total",
    "line": -110,
    "strategy": "fade_public/follow_sharps/stay_away",
    "reasoning": "Your bookmaker analysis",
    "confidence": 0.7,
    "stake_percentage": 0.02
}}"""

        response = self._call_claude(system_prompt, user_message)

        # Parse response
        try:
            analysis = self._parse_json_response(response)

            if not analysis.get("should_bet", False):
                return None

            # Bookies bet strategically, not often
            stake = self._calculate_bookie_stake(
                analysis.get("confidence", 0.6),
                analysis.get("stake_percentage", 0.02)
            )

            strategy_emoji = {
                "fade_public": "🚫",
                "follow_sharps": "🧠",
                "stay_away": "⚠️"
            }.get(analysis.get("strategy", "fade_public"), "📊")

            # Ensure line is numeric
            line = float(analysis.get("line", -110))
            confidence = float(analysis.get("confidence", 0.6))
            
            return Bet(
                game_id=game.id,
                team=analysis["bet_team"],
                bet_type=analysis["bet_type"],
                line=line,
                odds=self._american_to_decimal(line),
                stake=stake,
                confidence=confidence,
                reasoning=f"{strategy_emoji} BOOKIE PLAY: {analysis['reasoning']}",
                agent_name=self.name
            )

        except Exception as e:
            return None

    def predict_line_movement(self, game: Game, current_line: float) -> Dict[str, Any]:
        """Predict how the line will move based on public/sharp action.

        Args:
            game: Game to analyze
            current_line: Current betting line

        Returns:
            Prediction of line movement
        """
        system_prompt = f"""You are {self.name}, an expert bookmaker.

Predict how this line will move between now and game time based on:
- Public betting patterns
- Sharp money indicators
- Market efficiency
- Time until game"""

        user_message = f"""Game: {game.away_team} @ {game.home_team}
Current line: {current_line}

Will the line move? Which direction? Why?

JSON response:
{{
    "will_move": true/false,
    "direction": "up/down",
    "predicted_closing_line": -3.5,
    "reasoning": "why"
}}"""

        response = self._call_claude(system_prompt, user_message)

        try:
            return self._parse_json_response(response)
        except:
            return {"will_move": False, "reasoning": "Uncertain"}

    def _format_game_info(self, game: Game) -> str:
        """Format game information."""
        info = f"""{game.away_team} @ {game.home_team}
Current odds:
- {game.away_team}: {game.away_odds}
- {game.home_team}: {game.home_odds}
"""
        if game.home_spread:
            info += f"Spread: {game.home_team} {game.home_spread}\n"
        if game.over_under:
            info += f"Total: {game.over_under}\n"

        return info

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from Claude response."""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        return json.loads(response)

    def _calculate_bookie_stake(self, confidence: float, base_percentage: float) -> float:
        """Calculate stake - bookies are conservative.

        Args:
            confidence: Confidence in the play
            base_percentage: Base stake percentage

        Returns:
            Stake amount
        """
        # Bookies are conservative, they already have edge from juice
        conservative_multiplier = 0.8
        stake_percentage = base_percentage * conservative_multiplier

        return self.bankroll * min(stake_percentage, 0.03)  # Cap at 3%

    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
