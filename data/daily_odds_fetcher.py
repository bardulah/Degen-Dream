"""Daily odds fetcher - fetch what's actually available today."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from agents.base_agent import Game
from data.odds_api_client import OddsAPIClientV2
from data.scrapers import NikeScraper
from config.settings import settings


class DailyOddsFetcher:
    """Fetch odds for today's matchups - with sport/league/count filtering."""
    
    def __init__(
        self,
        use_nike: bool = True,
        use_odds_api: bool = False,
        filter_sports: Optional[List[str]] = None,
        filter_leagues: Optional[List[str]] = None,
        max_per_sport: Optional[int] = None
    ):
        """Initialize daily odds fetcher.
        
        Args:
            use_nike: Use Nike.sk scraper
            use_odds_api: Use TheOddsAPI
            filter_sports: Only include these sports (e.g., ['soccer', 'basketball'])
            filter_leagues: Only include these leagues (e.g., ['premier_league', 'la_liga'])
            max_per_sport: Limit games per sport (e.g., 5 games per sport max)
        """
        self.use_nike = use_nike
        self.use_odds_api = use_odds_api
        self.nike_scraper = NikeScraper() if use_nike else None
        self.odds_api = OddsAPIClientV2() if use_odds_api and settings.ODDS_API_KEY else None
        
        # Filtering options
        self.filter_sports = filter_sports
        self.filter_leagues = filter_leagues
        self.max_per_sport = max_per_sport
    
    def get_todays_games(
        self,
        hours_ahead: int = 24
    ) -> Dict[str, List[Game]]:
        """Get today's games by fetching what's actually available.
        
        Strategy:
        1. Nike.sk for all available sports (most reliable)
        2. OddsAPI - try all available sports, only keep games with matches today
        3. Merge results, deduplicate
        
        Args:
            hours_ahead: How many hours ahead to look
        
        Returns:
            Dict mapping sport name to list of games
        """
        results = {}
        now = datetime.utcnow()
        
        # Nike.sk for all available sports (most reliable)
        if self.use_nike:
            try:
                print("\n📅 Fetching from Nike.sk (All Sports)...")
                nike_games_by_sport = self.nike_scraper.get_all_sports()
                
                for sport, nike_games in nike_games_by_sport.items():
                    nike_games = self._filter_by_date(nike_games, now, hours_ahead)
                    
                    if nike_games:
                        if sport in results:
                            # Merge with existing
                            all_games = results[sport] + nike_games
                            results[sport] = self._deduplicate_games(all_games)
                        else:
                            results[sport] = self._deduplicate_games(nike_games)
                
                # Print Nike summary
                nike_total = sum(len(g) for g in results.values())
                if nike_total > 0:
                    print(f"  📦 Nike.sk Total: {nike_total} games")
            except Exception as e:
                print(f"  ⚠️  Nike.sk failed: {str(e)[:50]}")
        
        # OddsAPI - fetch all available sports and keep only games with matches today
        if self.use_odds_api and self.odds_api:
            print("\n📅 Fetching from TheOddsAPI (All Available Sports)...")
            
            try:
                # Get all available sports
                available_sports = self.odds_api.get_available_sports_with_games(hours_ahead=hours_ahead)
                
                if not available_sports:
                    print("  ⚠️  No sports with games found today")
                else:
                    print(f"  📊 Found {len(available_sports)} sports with games today")
                    
                    # Fetch odds for each sport with games
                    for sport_key in available_sports:
                        try:
                            games = self.odds_api.get_odds_for_sport(sport_key, hours_ahead=hours_ahead)
                            
                            if games:
                                # Map sport key to generic sport name
                                sport_name = self._map_sport_key_to_name(sport_key)
                                
                                # Merge with existing results (dedup across sources)
                                if sport_name in results:
                                    all_games = results[sport_name] + games
                                    results[sport_name] = self._deduplicate_games(all_games)
                                else:
                                    results[sport_name] = self._deduplicate_games(games)
                                
                                print(f"  ✅ {sport_key}: {len(games)} games")
                        except Exception as e:
                            print(f"  ⚠️  {sport_key} failed: {str(e)[:50]}")
                    
                    # Print OddsAPI stats
                    stats = self.odds_api.get_api_stats()
                    print(f"\n  📊 OddsAPI Stats:")
                    print(f"     Requests: {stats['requests_made']} (Success rate: {stats['success_rate']}%)")
                    print(f"     Health: {'🟢 Healthy' if stats['is_healthy'] else '🔴 Degraded'}")
            
            except Exception as e:
                print(f"  ⚠️  OddsAPI initialization failed: {str(e)[:50]}")
        
        # Apply filters
        results = self._apply_filters(results)
        
        # Summary
        print("\n" + "=" * 70)
        total = sum(len(g) for g in results.values())
        print(f"📊 TOTAL: {total} games across {len(results)} sports")
        if results:
            for sport, games in results.items():
                print(f"   • {sport.upper()}: {len(games)} games")
        else:
            print("   ⚠️  No games found - check API credentials or Nike.sk availability")
        print("=" * 70)
        
        return results
    
    def _apply_filters(self, games_by_sport: Dict[str, List[Game]]) -> Dict[str, List[Game]]:
        """Apply sport/league/count filters to games.
        
        Args:
            games_by_sport: Dict of sport -> list of games
        
        Returns:
            Filtered dict of sport -> list of games
        """
        result = {}
        
        for sport, games in games_by_sport.items():
            # Filter by sport
            if self.filter_sports and sport not in self.filter_sports:
                continue
            
            # Filter by league
            filtered_games = games
            if self.filter_leagues:
                filtered_games = [g for g in games if g.league in self.filter_leagues]
            
            # Limit per sport
            if self.max_per_sport and len(filtered_games) > self.max_per_sport:
                filtered_games = filtered_games[:self.max_per_sport]
            
            if filtered_games:
                result[sport] = filtered_games
        
        return result
    
    def get_available_leagues(self) -> Dict[str, set]:
        """Get all available leagues grouped by sport.
        
        Returns:
            Dict of sport -> set of league names
        """
        leagues_by_sport = {}
        
        if self.use_nike:
            try:
                games_by_sport = self.nike_scraper.get_all_sports()
                for sport, games in games_by_sport.items():
                    leagues = set(g.league for g in games if g.league)
                    if leagues:
                        leagues_by_sport[sport] = leagues
            except Exception as e:
                print(f"Error getting leagues from Nike: {e}")
        
        return leagues_by_sport
    
    def _map_sport_key_to_name(self, sport_key: str) -> str:
        """Map OddsAPI sport key to generic sport name.
        
        Args:
            sport_key: API sport key (e.g., 'soccer_epl', 'basketball_nba')
        
        Returns:
            Generic sport name (e.g., 'soccer', 'basketball')
        """
        mapping = {
            "soccer": "soccer",
            "basketball": "basketball",
            "hockey": "hockey",
            "american_football": "american_football",
            "baseball": "baseball",
            "tennis": "tennis",
            "golf": "golf"
        }
        
        # Extract base sport from key (first part before underscore)
        base_sport = sport_key.split('_')[0]
        return mapping.get(base_sport, base_sport)
    
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


if __name__ == "__main__":
    # Test: Fetch what's actually available today
    print("\n" + "=" * 70)
    print("TESTING DAILY ODDS FETCHER")
    print("=" * 70)
    fetcher = DailyOddsFetcher(
        use_nike=True,
        use_odds_api=True
    )
    
    games_by_sport = fetcher.get_todays_games()
    
    # Print sample games
    for sport, games in games_by_sport.items():
        print(f"\n{sport.upper()} ({len(games)} games):")
        for game in games[:3]:
            print(f"  • {game.home_team} vs {game.away_team} @ {game.home_odds}/{game.away_odds}")
