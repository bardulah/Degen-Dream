from data.scrapers import NikeScraper
import json

def test_scraper():
    scraper = NikeScraper()
    print("Scraping soccer games...")
    games = scraper.get_odds("soccer")
    
    print(f"Found {len(games)} games")
    for i, game in enumerate(games[:5]):
        print(f"Game {i+1}: {game.home_team} vs {game.away_team}")
        print(f"  Home: {game.home_odds}")
        print(f"  Draw: {game.draw_odds}")
        print(f"  Away: {game.away_odds}")
        print("-" * 20)

if __name__ == "__main__":
    test_scraper()
