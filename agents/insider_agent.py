"""Insider agent - claims to have inside information."""

import json
from typing import Dict, Optional, Any
from .base_agent import BaseAgent, AgentType, Bet, Game


class InsiderAgent(BaseAgent):
    """Insider bettor who claims inside information."""

    def __init__(self, name: str, personality_prompt: str, initial_bankroll: float = 1000.0):
        """Initialize insider agent."""
        super().__init__(name, AgentType.INSIDER, personality_prompt, initial_bankroll)
        self.leak_confidence = 0.85  # High confidence when they "have info"
        self.leak_probability = 0.15  # 15% chance they have "inside info" on any game

    def analyze_game(self, game: Game, context: Dict[str, Any]) -> Optional[Bet]:
        """Analyze game using insider knowledge (real or imagined).

        Args:
            game: Game to analyze
            context: Additional context

        Returns:
            Bet if insider has "information", None otherwise
        """
        system_prompt = f"""You are {self.name}, an insider bettor in the Bratislava Betting Syndicate.

{self.personality_prompt}

You have (or claim to have) inside information about:
- Player injuries (verify against real team news)
- Team news and locker room issues
- Referee assignments and tendencies
- Weather conditions
- Possible match-fixing (rare but you hint at it)

You're confident but sometimes overconfident. You speak in hushed tones about your "sources".

IMPORTANT: Base claims on actual team news/injuries provided. Don't hallucinate.

About {int(self.leak_probability * 100)}% of the time, you'll claim to have inside information on a game."""

        game_info = self._format_game_info(game)
        nike_data = context.get("nike_data", "No Niké data available")
        real_time_data = context.get("real_time_data", "")
        injury_news = context.get("injury_news", "")

        user_message = f"""Game to analyze:

{game_info}

REAL TEAM DATA (from web search):
{real_time_data}

{f"INJURY REPORTS:{chr(10)}{injury_news}" if injury_news else ""}

Niké Betting Data:
{nike_data}

Do you have any inside information on this game? Use actual team news above. If yes, what bet should we make?

Respond in JSON format:
{{
    "have_info": true/false,
    "info_type": "injury/fixing/weather/other",
    "bet_team": "team name",
    "bet_type": "moneyline/spread/total",
    "line": -110,
    "confidence": 0.85,
    "inside_scoop": "What you know (cite actual news if available)",
    "reasoning": "Why this info matters",
    "stake_percentage": 0.03
}}

If no inside info, return {{"have_info": false, "reasoning": "Nothing on this one"}}"""

        response = self._call_claude(system_prompt, user_message)

        # Parse response
        try:
            analysis = self._parse_json_response(response)

            if not analysis.get("have_info", False):
                return None

            # Insiders bet bigger when they "know something"
            stake = self._calculate_insider_stake(
                analysis.get("confidence", 0.8),
                analysis.get("stake_percentage", 0.03)
            )

            # Get actual odds from the game
            bet_team = analysis["bet_team"]
            if analysis["bet_type"].lower() == "total":
                odds = game.over_odds if "Over" in bet_team else game.under_odds
                if not odds:
                    odds = game.home_odds  # Fallback to moneyline
            else:
                odds = game.home_odds if bet_team == game.home_team else game.away_odds

            return Bet(
                game_id=game.id,
                team=analysis["bet_team"],
                bet_type=self.normalize_bet_type(analysis["bet_type"]),
                line=analysis["line"],
                odds=odds,
                stake=stake,
                confidence=analysis["confidence"],
                reasoning=f"🤫 {analysis['inside_scoop']} - {analysis['reasoning']}",
                agent_name=self.name
            )

        except Exception as e:
            print(f"Error analyzing game for {self.name}: {e}")
            return None

    def _format_game_info(self, game: Game) -> str:
        """Format game information."""
        return f"""{game.away_team} @ {game.home_team}
Sport: {game.sport}
Time: {game.commence_time}
Current lines: {game.away_team} {game.away_odds} / {game.home_team} {game.home_odds}"""

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

    def _calculate_insider_stake(self, confidence: float, base_percentage: float) -> float:
        """Calculate stake - insiders bet bigger on their info.

        Args:
            confidence: Confidence in the insider tip
            base_percentage: Base stake percentage

        Returns:
            Stake amount
        """
        # Insiders are aggressive when they "have information"
        multiplier = 1.5 if confidence > 0.8 else 1.0
        stake_percentage = base_percentage * multiplier

        return self.bankroll * min(stake_percentage, 0.05)  # Cap at 5%

    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
