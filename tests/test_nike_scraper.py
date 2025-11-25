#!/usr/bin/env python3
"""Test script for NikeScraper to verify it works with real data."""

import sys
sys.path.insert(0, '/home/matus/Projects/Degen-Dream')

from data.scrapers import NikeScraper

def test_nike_scraper():
    """Test the NikeScraper with real data from nike.sk"""
    print("Testing NikeScraper...")
    print("=" * 60)
    
    scraper = NikeScraper()
    games = scraper.get_odds()
    
    print(f"\nTotal games scraped: {len(games)}")
    print("=" * 60)
    
    if games:
        print("\nFirst 5 games:")
        for i, game in enumerate(games[:5], 1):
            print(f"\n{i}. {game.home_team} vs {game.away_team}")
            print(f"   Match ID: {game.id}")
            print(f"   Sport: {game.sport}")
            print(f"   Bookmaker: {game.bookmaker}")
            print(f"   Home odds: {game.home_odds}")
            print(f"   Away odds: {game.away_odds}")
            print(f"   Commence time: {game.commence_time}")
    else:
        print("\n⚠️  No games were scraped!")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Scraper test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_nike_scraper()
    sys.exit(0 if success else 1)
