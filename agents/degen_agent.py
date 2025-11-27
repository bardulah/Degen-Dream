"""Degen agent - chaos mode betting based on gut feelings."""

import json
import random
from typing import Dict, Optional, Any
from .base_agent import BaseAgent, AgentType, Bet, Game


class DegenAgent(BaseAgent):
    """Degenerate gambler who bets on gut feelings, superstitions, and YOLO energy."""

    def __init__(self, name: str, personality_prompt: str, initial_bankroll: float = 1000.0):
        """Initialize degen agent."""
        super().__init__(name, AgentType.DEGEN, personality_prompt, initial_bankroll)
        self.bet_frequency = 0.7  # Degens bet on 70% of games
        self.loves_parlays = True
        self.superstition_mode = random.choice([True, False])

    def analyze_game(self, game: Game, context: Dict[str, Any]) -> Optional[Bet]:
        """Analyze game using degen logic (gut feelings, vibes, chaos).

        Args:
            game: Game to analyze
            context: Ignored mostly, degens don't care about data

        Returns:
            Bet based on vibes, None if the spirits say no
        """
        # Degens bet frequently but randomly
        if random.random() > self.bet_frequency:
            return None

        system_prompt = f"""You are {self.name}, a degenerate gambler in the Bratislava Betting Syndicate.

{self.personality_prompt}

You bet based on:
- Gut feelings and vibes
- Team colors and mascots
- Lucky numbers
- Horoscopes and superstitions
- Revenge games
- "Due for a win" logic
- Parlays and long shots
- Complete randomness
- BUT ALSO: You check team news (for inspiration, not logic)

You YOLO into bets. You trust your gut over statistics. You love underdogs and overs.
You're here for the thrill, not the math. BE CHAOTIC."""

        game_info = self._format_game_info(game)
        moon_phase = random.choice(["waxing", "waning", "full", "new"])
        lucky_number = random.randint(1, 99)
        real_time_data = context.get("real_time_data", "")

        user_message = f"""Game:

{game_info}

{f"TEAM VIBES (for inspiration):{chr(10)}{real_time_data}" if real_time_data else ""}

Today's moon phase: {moon_phase}
Your lucky number today: {lucky_number}
Your gut feeling: {random.choice(['STRONG', 'eh', 'MEGA STRONG', 'iffy but send it'])}

What's the play? Go with your gut!

Respond in JSON:
{{
    "bet_team": "team name or total",
    "bet_type": "moneyline/spread/total",
    "line": -110,
    "confidence": 0.95,
    "vibe_check": "Why you feel it (be chaotic)",
    "stake_percentage": 0.05
}}

YOLO it!"""

        response = self._call_claude(system_prompt, user_message)

        # Parse response
        try:
            analysis = self._parse_json_response(response)

            # Degens bet aggressively
            stake = self._calculate_degen_stake(analysis.get("stake_percentage", 0.05))

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
                line=analysis.get("line", -110),
                odds=odds,
                stake=stake,
                confidence=analysis.get("confidence", 0.95),  # Degens are always confident
                reasoning=f"🎲 DEGEN ENERGY: {analysis.get('vibe_check', 'just feels right')}",
                agent_name=self.name
            )

        except Exception as e:
            # If parsing fails, just YOLO a random bet
            return self._yolo_random_bet(game)

    def _format_game_info(self, game: Game) -> str:
        """Format game information."""
        return f"""{game.away_team} @ {game.home_team}
{game.away_team}: {game.away_odds}
{game.home_team}: {game.home_odds}
Total: {game.over_under if game.over_under else 'N/A'}"""

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

    def _calculate_degen_stake(self, base_percentage: float) -> float:
        """Calculate stake - degens bet bigger and randomly.

        Args:
            base_percentage: Suggested stake percentage

        Returns:
            Stake amount (can be wild)
        """
        # Add randomness to stake size
        chaos_multiplier = random.uniform(0.8, 2.0)
        stake_percentage = base_percentage * chaos_multiplier

        # Degens sometimes send it ALL
        if random.random() < 0.05:  # 5% chance of huge bet
            stake_percentage = min(stake_percentage * 3, 0.15)

        return self.bankroll * min(stake_percentage, 0.15)  # Cap at 15%

    def _yolo_random_bet(self, game: Game) -> Bet:
        """Create a random YOLO bet when all else fails."""
        teams = [game.home_team, game.away_team]
        bet_types = ["moneyline", "spread", "total"]

        return Bet(
            game_id=game.id,
            team=random.choice(teams),
            bet_type=random.choice(bet_types),
            line=-110,
            odds=1.91,
            stake=self.bankroll * 0.05,
            confidence=0.99,  # Maximum degen confidence
            reasoning="🎲 FULL SEND MODE - No thoughts, just vibes",
            agent_name=self.name
        )

    def _american_to_decimal(self, american_odds: float) -> float:
        """Convert American odds to decimal."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
