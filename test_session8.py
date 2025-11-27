#!/usr/bin/env python3
"""Test Session 8 improvements: LeagueSelector and OddsAPIClientV2."""

import sys
from datetime import datetime

def test_league_selector():
    """Test LeagueSelector functionality."""
    print("\n" + "=" * 70)
    print("TEST 1: League Selector")
    print("=" * 70)
    
    try:
        from data.league_selector import LeagueSelector, AgentProfile
        
        # Test 1a: Recommend leagues
        print("\n1a. Recommending leagues for default agent composition...")
        rec = LeagueSelector.recommend_league_selection(
            num_sharps=3,
            num_insiders=2,
            num_degens=3,
            num_bookies=2
        )
        
        assert rec['selected_leagues'], "No leagues selected"
        assert len(rec['selected_leagues']) > 0, "Empty league list"
        print(f"   ✅ Selected {len(rec['selected_leagues'])} leagues")
        
        # Test 1b: Verify scoring
        print("\n1b. Verifying agent type scoring...")
        for league in rec['selected_leagues'][:2]:
            sharp_score = league.get_score_for_agent(AgentProfile.SHARP)
            degen_score = league.get_score_for_agent(AgentProfile.DEGEN)
            assert 0 <= sharp_score <= 100, f"Invalid sharp score: {sharp_score}"
            assert 0 <= degen_score <= 100, f"Invalid degen score: {degen_score}"
        print(f"   ✅ Scoring works (scores 0-100)")
        
        # Test 1c: Sport grouping
        print("\n1c. Grouping leagues by sport...")
        sports = LeagueSelector.get_sports_with_available_games(rec['selected_leagues'])
        assert 'soccer' in sports, "No soccer leagues"
        assert 'basketball' in sports, "No basketball leagues"
        print(f"   ✅ Sports grouped: {', '.join(sorted(sports.keys()))}")
        
        # Test 1d: Custom composition
        print("\n1d. Testing custom agent composition...")
        rec_custom = LeagueSelector.recommend_league_selection(
            num_sharps=5,
            num_insiders=0,
            num_degens=1,
            num_bookies=4
        )
        assert rec_custom['selected_leagues'], "No leagues for custom composition"
        print(f"   ✅ Custom composition works (selected {len(rec_custom['selected_leagues'])} leagues)")
        
        print("\n✅ League Selector: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ League Selector FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_odds_api_client():
    """Test OddsAPIClientV2 functionality."""
    print("\n" + "=" * 70)
    print("TEST 2: OddsAPI Client V2")
    print("=" * 70)
    
    try:
        from data.odds_api_client import OddsAPIClientV2
        
        # Test 2a: Instantiation
        print("\n2a. Creating OddsAPI client...")
        client = OddsAPIClientV2(api_key="test_key")
        print(f"   ✅ Client created")
        
        # Test 2b: Health check
        print("\n2b. Checking API health...")
        is_healthy = client.is_healthy()
        assert isinstance(is_healthy, bool), "Health check should return bool"
        print(f"   ✅ API health: {is_healthy}")
        
        # Test 2c: Cache methods
        print("\n2c. Testing cache methods...")
        from agents.base_agent import Game
        test_game = Game(
            id="test_001",
            home_team="Test Home",
            away_team="Test Away",
            sport="soccer",
            commence_time=datetime.utcnow().isoformat(),
            bookmaker="test",
            home_odds=2.0,
            away_odds=2.0
        )
        
        client._cache_result("test_league", [test_game])
        cached = client._get_from_cache("test_league")
        assert cached is not None, "Cache failed"
        assert len(cached) == 1, "Cache should have 1 game"
        print(f"   ✅ Cache working (TTL={client.cache_ttl_minutes} min)")
        
        # Test 2d: API stats
        print("\n2d. Getting API stats...")
        stats = client.get_api_stats()
        assert 'requests_made' in stats, "Stats missing requests_made"
        assert 'success_rate' in stats, "Stats missing success_rate"
        assert 'is_healthy' in stats, "Stats missing is_healthy"
        print(f"   ✅ API stats: {stats['requests_made']} requests, "
              f"{stats['success_rate']}% success, healthy={stats['is_healthy']}")
        
        # Test 2e: Cache clearing
        print("\n2e. Testing cache clearing...")
        client.clear_cache()
        assert len(client.league_cache) == 0, "Cache not cleared"
        print(f"   ✅ Cache cleared")
        
        print("\n✅ OddsAPI Client V2: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ OddsAPI Client V2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_daily_odds_fetcher():
    """Test DailyOddsFetcher integration."""
    print("\n" + "=" * 70)
    print("TEST 3: Daily Odds Fetcher Integration")
    print("=" * 70)
    
    try:
        from data.daily_odds_fetcher import DailyOddsFetcher
        
        # Test 3a: Instantiation with smart selection
        print("\n3a. Creating fetcher with smart league selection...")
        fetcher = DailyOddsFetcher(
            use_nike=False,  # Skip Nike.sk (requires browser automation)
            use_odds_api=False,  # Skip OddsAPI (requires API key)
            use_smart_league_selection=True,
            num_sharps=3,
            num_insiders=2,
            num_degens=3,
            num_bookies=2
        )
        print(f"   ✅ Fetcher created with {len(fetcher.selected_leagues)} leagues")
        
        # Test 3b: Verify selected leagues
        print("\n3b. Verifying selected leagues...")
        assert len(fetcher.selected_leagues) > 0, "No leagues selected"
        for league in fetcher.selected_leagues:
            assert hasattr(league, 'key'), f"League missing key: {league}"
            assert hasattr(league, 'name'), f"League missing name: {league}"
            assert hasattr(league, 'sport'), f"League missing sport: {league}"
        print(f"   ✅ All {len(fetcher.selected_leagues)} leagues valid")
        
        # Test 3c: League grouping
        print("\n3c. Grouping leagues by sport...")
        from data.league_selector import LeagueSelector
        sports = LeagueSelector.get_sports_with_available_games(fetcher.selected_leagues)
        print(f"   ✅ Sports covered: {', '.join(sorted(sports.keys()))}")
        
        # Test 3d: Deduplication logic
        print("\n3d. Testing deduplication logic...")
        from agents.base_agent import Game
        games = [
            Game(
                id="game1",
                home_team="Team A",
                away_team="Team B",
                sport="soccer",
                commence_time=datetime.utcnow().isoformat(),
                bookmaker="nike",
                home_odds=2.0,
                away_odds=2.0
            ),
            Game(
                id="game2",
                home_team="Team A",  # Same teams
                away_team="Team B",
                sport="soccer",
                commence_time=datetime.utcnow().isoformat(),
                bookmaker="draftkings",
                home_odds=2.1,  # Better odds
                away_odds=2.1
            )
        ]
        deduped = fetcher._deduplicate_games(games)
        assert len(deduped) == 1, f"Dedup failed: {len(deduped)} games instead of 1"
        assert deduped[0].home_odds == 2.1, "Didn't keep best odds"
        print(f"   ✅ Deduplication works (kept best odds)")
        
        print("\n✅ Daily Odds Fetcher: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ Daily Odds Fetcher FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("SESSION 8 INTEGRATION TESTS")
    print("=" * 70)
    
    results = {}
    
    results['league_selector'] = test_league_selector()
    results['odds_api_client'] = test_odds_api_client()
    results['daily_odds_fetcher'] = test_daily_odds_fetcher()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
