#!/usr/bin/env python3
"""Quick test script for Discord notifications."""

import asyncio
import os
from notification.discord_notifier import DiscordNotifier


async def main():
    """Test Discord webhook."""
    notifier = DiscordNotifier()
    
    if not notifier.enabled:
        print("❌ DISCORD_WEBHOOK_URL not set in .env")
        print("   Get webhook URL from Discord server → Integrations → Webhooks")
        return
    
    print("✅ Discord webhook found")
    print(f"   URL: {notifier.webhook_url[:50]}...")
    
    # Test 1: Simple message
    print("\n📤 Test 1: Sending simple message...")
    result = await notifier.send_message("🎰 Testing Bratislava Betting Syndicate Discord bot!")
    if result:
        print("   ✅ Message sent!")
    else:
        print("   ❌ Failed to send")
        return
    
    await asyncio.sleep(1)
    
    # Test 2: Embed with fields
    print("\n📤 Test 2: Sending embed with fields...")
    result = await notifier.send_embed(
        title="🧠 Agent Test",
        fields={
            "Agent": "Viktor (Sharp)",
            "Pick": "Barcelona",
            "Odds": "1.85",
            "Stake": "€150.00",
            "Confidence": "▓▓▓▓▓▓░░░░ 65%"
        },
        color=16776960  # Gold
    )
    if result:
        print("   ✅ Embed sent!")
    else:
        print("   ❌ Failed to send")
        return
    
    await asyncio.sleep(1)
    
    # Test 3: Oracle decision
    print("\n📤 Test 3: Sending Oracle decision...")
    from agents.base_agent import Bet
    
    test_bet = Bet(
        game_id="test_game",
        team="Barcelona",
        bet_type="moneyline",
        line=-110,
        odds=1.85,
        stake=150.0,
        confidence=0.78,
        reasoning="Line moved 5 cents to Barcelona, indicates sharp action",
        agent_name="Oracle"
    )
    
    result = await notifier.on_oracle_decision(
        test_bet,
        {"Barcelona": 6, "Real Madrid": 4}
    )
    if result:
        print("   ✅ Oracle decision sent!")
    else:
        print("   ❌ Failed to send")
        return
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\nCheck your Discord channel for messages!")
    print("\nNow run:")
    print("  python main.py --games 3 --sample --no-live")


if __name__ == "__main__":
    asyncio.run(main())
