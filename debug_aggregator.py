from data.odds_aggregator import OddsAggregator
import json

def test_aggregator():
    print("Initializing Aggregator...")
    aggregator = OddsAggregator()
    
    print("Fetching all odds...")
    games = aggregator.get_all_odds("soccer")
    
    print(f"Found {len(games)} games")
    for i, game in enumerate(games[:5]):
        print(f"Game {i+1}: {game.home_team} vs {game.away_team}")
        print(f"  Home: {game.home_odds}")
        print(f"  Draw: {game.draw_odds}")
        print(f"  Away: {game.away_odds}")
        print(f"  Bookmaker: {game.bookmaker}")
        print("-" * 20)

if __name__ == "__main__":
    test_aggregator()
