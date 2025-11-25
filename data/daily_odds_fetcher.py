"""Daily odds fetcher with date and league filtering."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from agents.base_agent import Game
from data.odds_api import OddsAPIClient
from data.scrapers import NikeScraper
from data.odds_aggregator import OddsAggregator
from config.settings import settings


# Top leagues by sport
TOP_LEAGUES = {
    "soccer": [
        "soccer_epl",           # English Premier League
        "soccer_spain_la_liga", # Spanish La Liga
        "soccer_germany_bundesliga",  # German Bundesliga
        "soccer_italy_serie_a", # Italian Serie A
        "soccer_france_ligue_1", # French Ligue 1
    ],
    "basketball": [
        "basketball_nba",       # NBA
        "basketball_euroleague", # EuroLeague
    ],
    "hockey": [
        "hockey_nhl",           # NHL
    ],
    "tennis": [
        "tennis_atp",           # ATP
        "tennis_wta",           # WTA
    ]
}


class DailyOddsFetcher:
    """Fetch odds for today's matchups from top leagues only."""
    
    def __init__(self, use_nike: bool = True, use_odds_api: bool = True):
        """Initialize daily odds fetcher.
        
        Args:
            use_nike: Use Nike.sk scraper (good for soccer)
            use_odds_api: Use TheOddsAPI (good for multiple sports)
        """
        self.use_nike = use_nike
        self.use_odds_api = use_odds_api
        self.nike_scraper = NikeScraper() if use_nike else None
        self.odds_api = OddsAPIClient() if use_odds_api and settings.ODDS_API_KEY else None
    
    def get_todays_games(
        self,
        sports: Optional[List[str]] = None,
        hours_ahead: int = 24
    ) -> Dict[str, List[Game]]:
        """Get today's games for specified sports.
        
        Args:
            sports: List of sports ('soccer', 'basketball', 'hockey', 'tennis')
                    If None, fetches all
            hours_ahead: How many hours ahead to look (default: 24 = today + tomorrow)
        
        Returns:
            Dict mapping sport name to list of games
        """
        if sports is None:
            sports = list(TOP_LEAGUES.keys())
        
        results = {}
        now = datetime.utcnow()
        
        for sport in sports:
            print(f"\n📅 Fetching {sport.upper()} for today...")
            
            games = []
            
            # Nike scraper - primarily for soccer
            if self.use_nike and sport == "soccer":
                try:
                    nike_games = self.nike_scraper.get_odds("soccer")
                    # Filter to today's games
                    nike_games = self._filter_by_date(nike_games, now, hours_ahead)
                    games.extend(nike_games)
                    print(f"  ✓ Nike.sk: {len(nike_games)} games")
                except Exception as e:
                    print(f"  ✗ Nike.sk failed: {e}")
            
            # OddsAPI - for all sports
            if self.use_odds_api:
                try:
                    for league_key in TOP_LEAGUES.get(sport, []):
                        api_games = self.odds_api.get_odds(sport=league_key)
                        # Filter to today's games
                        api_games = self._filter_by_date(api_games, now, hours_ahead)
                        games.extend(api_games)
                    
                    # Deduplicate
                    games = self._deduplicate_games(games)
                    print(f"  ✓ OddsAPI: {len(games)} games")
                except Exception as e:
                    print(f"  ✗ OddsAPI failed: {e}")
            
            if games:
                results[sport] = games
            else:
                print(f"  ⚠ No games found for {sport}")
        
        # Print summary
        print("\n" + "=" * 60)
        total = sum(len(g) for g in results.values())
        print(f"📊 TOTAL: {total} games across {len(results)} sports")
        print("=" * 60)
        
        return results
    
    def _filter_by_date(
        self,
        games: List[Game],
        reference_time: datetime,
        hours_ahead: int = 24
    ) -> List[Game]:
        """Filter games to those within the next N hours.
        
        Args:
            games: List of games
            reference_time: Time to filter from (usually now)
            hours_ahead: How many hours ahead to include
        
        Returns:
            Filtered list of games
        """
        cutoff = reference_time + timedelta(hours=hours_ahead)
        filtered = []
        
        for game in games:
            try:
                game_time = datetime.fromisoformat(game.commence_time.replace('Z', '+00:00'))
                if reference_time <= game_time <= cutoff:
                    filtered.append(game)
            except (ValueError, TypeError):
                # If can't parse time, skip
                continue
        
        return filtered
    
    def _deduplicate_games(self, games: List[Game]) -> List[Game]:
        """Remove duplicate games (same teams, similar time).
        
        Args:
            games: List of games (possibly with duplicates)
        
        Returns:
            Deduplicated list
        """
        seen = {}
        deduped = []
        
        for game in games:
            # Create unique key from teams (ignoring order variations)
            teams_key = tuple(sorted([
                game.home_team.lower().strip(),
                game.away_team.lower().strip()
            ]))
            
            if teams_key not in seen:
                seen[teams_key] = game
                deduped.append(game)
            else:
                # Keep game with better odds (higher for home, lower for away)
                existing = seen[teams_key]
                if game.home_odds > existing.home_odds:
                    # Replace with better odds
                    deduped.remove(existing)
                    deduped.append(game)
                    seen[teams_key] = game
        
        return deduped


# Test function
if __name__ == "__main__":
    fetcher = DailyOddsFetcher(use_nike=True, use_odds_api=True)
    
    # Get today's top leagues
    games_by_sport = fetcher.get_todays_games(
        sports=["soccer", "basketball", "hockey", "tennis"]
    )
    
    # Print details
    for sport, games in games_by_sport.items():
        print(f"\n{sport.upper()} ({len(games)} games):")
        for game in games[:5]:  # Show first 5
            print(f"  • {game.home_team} vs {game.away_team}")
            print(f"    Odds: {game.home_odds} / {game.away_odds}")
