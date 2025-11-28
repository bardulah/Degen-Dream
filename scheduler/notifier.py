"""
Notification System - Send alerts via Discord, Telegram, and Email.

Configure with environment variables:
    DISCORD_WEBHOOK_URL - Discord webhook URL
    TELEGRAM_BOT_TOKEN - Telegram bot token
    TELEGRAM_CHAT_ID - Your Telegram chat ID
    NOTIFICATION_EMAIL - Email address for notifications
"""

import os
import requests
from typing import Dict, Optional
from datetime import datetime


class DiscordNotifier:
    """Send notifications via Discord webhook."""

    def __init__(self):
        """Initialize Discord notifier."""
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)

    def send_result_update(self, stats: Dict) -> bool:
        """
        Send result update notification to Discord.

        Args:
            stats: Statistics dictionary from result update

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False

        # Build message
        embed = {
            "title": "🎰 Betting Results Updated!",
            "description": f"New results fetched at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "color": 3066993,  # Green
            "fields": [
                {
                    "name": "📊 Summary",
                    "value": f"Checked: {stats['total_checked']} bets\nUpdated: {stats['updated']} bets",
                    "inline": True
                },
                {
                    "name": "📈 Results",
                    "value": f"✅ Won: {stats['won']}\n❌ Lost: {stats['lost']}\n⚪ Push: {stats['push']}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Bratislava Betting Syndicate"
            },
            "timestamp": datetime.now().isoformat()
        }

        # Add win rate if we have results
        if stats['won'] + stats['lost'] > 0:
            win_rate = (stats['won'] / (stats['won'] + stats['lost'])) * 100
            embed['fields'].append({
                "name": "🎯 Win Rate",
                "value": f"{win_rate:.1f}%",
                "inline": False
            })

        payload = {
            "embeds": [embed]
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Discord notification failed: {e}")
            return False

    def send_simulation_complete(self, simulation_id: str, roi: float, win_rate: float, profit: float):
        """Send notification when simulation completes."""
        if not self.enabled:
            return False

        color = 3066993 if roi > 0 else 15158332  # Green if positive, red if negative

        embed = {
            "title": "🎲 Simulation Complete!",
            "color": color,
            "fields": [
                {
                    "name": "Simulation ID",
                    "value": f"`{simulation_id[:16]}...`",
                    "inline": False
                },
                {
                    "name": "💰 ROI",
                    "value": f"**{roi:+.2f}%**",
                    "inline": True
                },
                {
                    "name": "🎯 Win Rate",
                    "value": f"{win_rate:.1f}%",
                    "inline": True
                },
                {
                    "name": "💵 Profit",
                    "value": f"€{profit:+,.2f}",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat()
        }

        payload = {"embeds": [embed]}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Discord notification failed: {e}")
            return False

    def send_bet_alert(self, bet_info: Dict):
        """Send alert for high-value bet opportunity."""
        if not self.enabled:
            return False

        embed = {
            "title": "🔥 High-Value Bet Alert!",
            "color": 16776960,  # Gold
            "fields": [
                {
                    "name": "🏟️ Game",
                    "value": f"{bet_info['away_team']} @ {bet_info['home_team']}",
                    "inline": False
                },
                {
                    "name": "📌 Recommendation",
                    "value": f"{bet_info['bet_type']} on {bet_info['team']}",
                    "inline": True
                },
                {
                    "name": "💰 Odds",
                    "value": f"{bet_info['odds']}",
                    "inline": True
                },
                {
                    "name": "🎯 Confidence",
                    "value": f"{bet_info['confidence']*100:.0f}%",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat()
        }

        if 'reasoning' in bet_info:
            embed['description'] = bet_info['reasoning']

        payload = {"embeds": [embed]}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Discord notification failed: {e}")
            return False


class TelegramNotifier:
    """Send notifications via Telegram bot."""

    def __init__(self):
        """Initialize Telegram notifier."""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def _send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """Send a message to Telegram."""
        if not self.enabled:
            return False

        url = f"{self.api_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False

    def send_result_update(self, stats: Dict) -> bool:
        """Send result update notification."""
        if stats['won'] + stats['lost'] > 0:
            win_rate = (stats['won'] / (stats['won'] + stats['lost'])) * 100
        else:
            win_rate = 0

        message = f"""
🎰 *Betting Results Updated!*

📊 *Summary:*
• Checked: {stats['total_checked']} bets
• Updated: {stats['updated']} bets

📈 *Results:*
• ✅ Won: {stats['won']}
• ❌ Lost: {stats['lost']}
• ⚪ Push: {stats['push']}

🎯 *Win Rate:* {win_rate:.1f}%

_Updated at {datetime.now().strftime('%Y-%m-%d %H:%M')}_
        """.strip()

        return self._send_message(message)

    def send_simulation_complete(self, simulation_id: str, roi: float, win_rate: float, profit: float):
        """Send notification when simulation completes."""
        emoji = "🔥" if roi > 10 else "✅" if roi > 0 else "❌"

        message = f"""
{emoji} *Simulation Complete!*

🆔 `{simulation_id[:16]}...`

💰 *ROI:* {roi:+.2f}%
🎯 *Win Rate:* {win_rate:.1f}%
💵 *Profit:* €{profit:+,.2f}

_Completed at {datetime.now().strftime('%Y-%m-%d %H:%M')}_
        """.strip()

        return self._send_message(message)

    def send_bet_alert(self, bet_info: Dict):
        """Send alert for high-value bet opportunity."""
        message = f"""
🔥 *High-Value Bet Alert!*

🏟️ *Game:*
{bet_info['away_team']} @ {bet_info['home_team']}

📌 *Recommendation:*
{bet_info['bet_type']} on {bet_info['team']}

💰 *Odds:* {bet_info['odds']}
🎯 *Confidence:* {bet_info['confidence']*100:.0f}%

{bet_info.get('reasoning', '')}
        """.strip()

        return self._send_message(message)


class EmailNotifier:
    """Send notifications via email (using SMTP)."""

    def __init__(self):
        """Initialize email notifier."""
        # Would need SMTP configuration
        self.enabled = False  # Placeholder for future implementation

    def send_result_update(self, stats: Dict) -> bool:
        """Send result update email."""
        # TODO: Implement SMTP email sending
        return False


# Test function
def test_notifications():
    """Test notification systems."""
    print("Testing notification systems...\n")

    # Test stats
    test_stats = {
        'total_checked': 10,
        'updated': 8,
        'won': 5,
        'lost': 3,
        'push': 0
    }

    # Test Discord
    discord = DiscordNotifier()
    if discord.enabled:
        print("📢 Testing Discord...")
        discord.send_result_update(test_stats)
        print("✅ Discord test sent")
    else:
        print("⚠️  Discord not configured (set DISCORD_WEBHOOK_URL)")

    print()

    # Test Telegram
    telegram = TelegramNotifier()
    if telegram.enabled:
        print("📢 Testing Telegram...")
        telegram.send_result_update(test_stats)
        print("✅ Telegram test sent")
    else:
        print("⚠️  Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")


if __name__ == '__main__':
    test_notifications()
