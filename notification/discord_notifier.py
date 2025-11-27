"""Discord webhook notifications for betting predictions."""

import aiohttp
import asyncio
import os
from typing import Optional, Dict, Any
from datetime import datetime


# Sport code to display name mapping
SPORT_NAMES = {
    "demo": "Demo/Sample Data",
    "soccer_epl": "Soccer - EPL",
    "soccer_la_liga": "Soccer - La Liga",
    "soccer_serie_a": "Soccer - Serie A",
    "soccer_bundesliga": "Soccer - Bundesliga",
    "soccer_ligue_1": "Soccer - Ligue 1",
    "nfl": "NFL",
    "nba": "NBA",
    "mlb": "MLB",
    "nhl": "NHL",
    "multi-sport": "Multi-Sport",
    "soccer": "Soccer"
}


def format_sport_name(sport_code: str) -> str:
    """Convert sport code to readable name."""
    return SPORT_NAMES.get(sport_code.lower(), sport_code.upper())


class DiscordNotifier:
    """Send real-time notifications to Discord webhook."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize Discord notifier.
        
        Args:
            webhook_url: Discord webhook URL (defaults to env var)
        """
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            print("⚠️  Discord webhook not configured - notifications disabled")
    
    async def send_message(self, content: str) -> bool:
        """Send plain text message.
        
        Args:
            content: Message content
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        payload = {
            "content": content,
            "username": "Betting Syndicate Bot",
            "avatar_url": "https://em-content.zeddicus.com/thumbs/openmoji/1.18.0/f0-9f-a4-96.png"  # Robot emoji
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 204:
                        return True
                    else:
                        print(f"❌ Discord error: HTTP {resp.status}")
                        return False
        except asyncio.TimeoutError:
            print("❌ Discord timeout")
            return False
        except Exception as e:
            print(f"❌ Discord send failed: {e}")
            return False
    
    async def send_embed(self, title: str, fields: Dict[str, str], 
                        color: int = 16776960, thumbnail_url: str = None) -> bool:
        """Send rich embed message with fields.
        
        Args:
            title: Embed title
            fields: Dict of field_name -> field_value
            color: Decimal color code (16776960 = gold)
            thumbnail_url: URL for small image
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        # Limit fields to avoid exceeding Discord limits
        field_list = []
        for k, v in list(fields.items())[:25]:  # Max 25 fields
            # Truncate long values
            v_str = str(v)[:1024]
            field_list.append({
                "name": str(k)[:256],
                "value": v_str,
                "inline": True
            })
        
        embed = {
            "title": title,
            "fields": field_list,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}
        
        payload = {
            "embeds": [embed],
            "username": "Betting Syndicate Bot"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 204:
                        return True
                    else:
                        print(f"❌ Discord error: HTTP {resp.status}")
                        return False
        except asyncio.TimeoutError:
            print("❌ Discord timeout")
            return False
        except Exception as e:
            print(f"❌ Discord send failed: {e}")
            return False
    
    # ─────────────────────────────────────────────────────────────────────
    # Agent-specific notification methods
    # ─────────────────────────────────────────────────────────────────────
    
    async def on_game_start(self, game) -> bool:
        """Notify when game analysis starts."""
        message = (
            f"⚽ **NEW GAME**: {game.away_team} @ {game.home_team}\n"
            f"🕐 Commence time: {game.commence_time}\n"
            f"🏟️  Analyzing now..."
        )
        return await self.send_message(message)
    
    async def on_agent_analyzed(self, agent_name: str, agent_type: str, bet) -> bool:
        """Notify when agent finishes analysis.

        Args:
            agent_name: Name of agent
            agent_type: Type (sharp, insider, degen, bookie)
            bet: Bet object or None if pass

        Returns:
            True if sent
        """
        emoji_map = {
            "sharp": "🧠",
            "insider": "🤫",
            "degen": "🎲",
            "bookie": "📊"
        }
        emoji = emoji_map.get(agent_type, "🤖")

        if bet is None:
            message = f"{emoji} {agent_name} (PASS) - No value found"
        else:
            confidence_bar = self._confidence_bar(bet.confidence)
            # Single line: emoji + name + team + odds + stake + confidence
            header = f"{emoji} {agent_name} ({agent_type.upper()}) | ✅ {bet.team} @ {bet.odds:.2f} | 💰 €{bet.stake:.2f} | {confidence_bar} {bet.confidence:.0%}"
            # Reasoning on next line (Discord has 2000 char limit, ~600 is safe)
            reasoning = f"└─ {bet.reasoning[:600]}"
            message = f"{header}\n{reasoning}"

        return await self.send_message(message)
    
    async def send_separator(self) -> bool:
        """Send a separator line between agents."""
        return await self.send_message("─" * 60)
    
    async def on_debate_message(self, agent_name: str, message: str) -> bool:
        """Notify during debate phase.
        
        Args:
            agent_name: Agent speaking
            message: What they said
            
        Returns:
            True if sent
        """
        # Keep full reasoning in chat
        content = f"🗣️ **{agent_name}**:\n{message}"
        # Discord message limit is 2000 chars, truncate if necessary
        if len(content) > 1900:
            content = content[:1900] + "..."
        return await self.send_message(content)
    
    async def on_oracle_decision(self, consensus_bet, agent_votes: Dict[str, int]) -> bool:
        """Notify when Oracle makes final decision.
        
        Args:
            consensus_bet: Final bet decision
            agent_votes: Dict of team -> vote count
            
        Returns:
            True if sent
        """
        vote_breakdown = " vs ".join([
            f"{team} ({votes})" 
            for team, votes in sorted(agent_votes.items(), key=lambda x: x[1], reverse=True)
        ]) or "No votes recorded"
        
        # Get matchup info if available
        matchup = getattr(consensus_bet, 'matchup', 'Unknown Matchup')
        
        # Get full reasoning without truncation
        reasoning = getattr(consensus_bet, 'reasoning', 'No reasoning provided')
        if reasoning and len(reasoning) > 500:
            reasoning = reasoning[:500] + "..."
        
        color = 3066993 if consensus_bet.team == "home" else 15158332  # Green or Red
        
        fields = {
            "⚽ Matchup": f"**{matchup}**",
            "🎯 Final Pick": f"**{consensus_bet.team}**",
            "🗳️  Votes": vote_breakdown if vote_breakdown != "No votes recorded" else "Votes TBD",
            "💰 Stake": f"€{consensus_bet.stake:.2f}",
            "📊 Odds": f"{consensus_bet.odds:.2f}",
            "🔥 Confidence": f"{consensus_bet.confidence:.0%}",
            "💭 Reasoning": reasoning or "No reasoning"
        }
        
        return await self.send_embed(
            title="🔮 ORACLE'S DECISION",
            fields=fields,
            color=color
        )
    
    async def on_simulation_start(self, num_games: int, sport: str) -> bool:
        """Notify when simulation starts."""
        formatted_sport = format_sport_name(sport)
        message = (
            f"🚀 **SIMULATION STARTED**\n"
            f"📊 Games to analyze: {num_games}\n"
            f"⚽ Sport: {formatted_sport}\n"
            f"👥 10 agents ready to debate..."
        )
        return await self.send_message(message)
    
    async def on_simulation_complete(self, num_games: int, total_wagered: float) -> bool:
        """Notify when simulation completes."""
        message = (
            f"✅ **SIMULATION COMPLETE**\n"
            f"📊 Games analyzed: {num_games}\n"
            f"💰 Total wagered: €{total_wagered:.2f}\n"
            f"📧 Report sent to email"
        )
        return await self.send_message(message)
    
    async def on_error(self, error_message: str) -> bool:
        """Notify on error."""
        message = f"⚠️  **ERROR**: {error_message}"
        return await self.send_message(message)
    
    # ─────────────────────────────────────────────────────────────────────
    # Utility methods
    # ─────────────────────────────────────────────────────────────────────
    
    @staticmethod
    def _confidence_bar(confidence: float, length: int = 10) -> str:
        """Generate ASCII confidence bar.
        
        Args:
            confidence: Confidence as decimal (0-1)
            length: Bar length
            
        Returns:
            Bar string (filled ▓ and empty ░)
        """
        filled = int(confidence * length)
        return "▓" * filled + "░" * (length - filled)


# Discord embed color codes (decimal format)
DISCORD_COLORS = {
    "gold": 16776960,      # Gold
    "green": 3066993,      # Green
    "red": 15158332,       # Red
    "blue": 3447003,       # Blue
    "purple": 9807270,     # Purple
    "orange": 15105570,    # Orange
}
