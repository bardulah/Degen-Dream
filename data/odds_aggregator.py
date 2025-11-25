"""Odds aggregator that combines multiple data sources."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fuzzywuzzy import fuzz
from agents.base_agent import Game
from data.odds_api import OddsAPIClient
from data.scrapers import NikeScraper
from data.flashscore_wrapper import FlashscoreWrapper
from config.settings import settings


class OddsAggregator:
    """Aggregates odds from multiple sources and provides best available odds."""
    
    def __init__(self):
        """Initialize odds aggregator with all data sources."""
        self.odds_api = OddsAPIClient() if settings.ODDS_API_KEY else None
        self.nike_scraper = NikeScraper()
        self.flashscore = FlashscoreWrapper()
        
        # Configuration
        self.use_odds_api = getattr(settings, 'USE_ODDS_API', True)
        self.use_nike = getattr(settings, 'USE_NIKE_SCRAPER', True)
        self.use_flashscore = getattr(settings, 'USE_FLASHSCORE', False)  # Default off until tested
        
        self.fuzzy_threshold = getattr(settings, 'FUZZY_MATCH_THRESHOLD', 85)
        self.max_time_diff_hours = getattr(settings, 'MAX_TIME_DIFF_HOURS', 24)
    
    def get_all_odds(self, sport: str = 'soccer') -> List[Game]:
        """Fetch odds from all enabled sources.
        
        Args:
            sport: Sport to get odds for
            
        Returns:
            List of Game objects with best available odds
        """
        all_games = []
        
        # Fetch from OddsAPI
        if self.use_odds_api and self.odds_api:
            try:
                print("Fetching from TheOddsAPI...")
                api_games = self.odds_api.get_odds(sport='soccer_epl')
                all_games.extend([(g, 'odds_api') for g in api_games])
                print(f"✓ Got {len(api_games)} games from OddsAPI")
            except Exception as e:
                print(f"✗ OddsAPI failed: {e}")
        
        # Fetch from Nike scraper
        if self.use_nike:
            try:
                print("Fetching from Nike.sk...")
                nike_games = self.nike_scraper.get_odds(sport)
                all_games.extend([(g, 'nike') for g in nike_games])
                print(f"✓ Got {len(nike_games)} games from Nike")
            except Exception as e:
                print(f"✗ Nike scraper failed: {e}")
        
        # Fetch from Flashscore
        if self.use_flashscore:
            try:
                print("Fetching from Flashscore...")
                flash_games = self.flashscore.get_odds(sport='football')
                all_games.extend([(g, 'flashscore') for g in flash_games])
                print(f"✓ Got {len(flash_games)} games from Flashscore")
            except Exception as e:
                print(f"✗ Flashscore scraper failed: {e}")
        
        if not all_games:
            print("⚠ No games fetched from any source!")
            return []
        
        # Deduplicate and merge odds
        unique_games = self._deduplicate_and_merge(all_games)
        
        print(f"\n📊 Total: {len(unique_games)} unique games from {len(all_games)} total")
        return unique_games
    
    def _deduplicate_and_merge(self, games_with_sources: List[tuple]) -> List[Game]:
        """Deduplicate games and merge odds from multiple sources.
        
        Args:
            games_with_sources: List of (Game, source_name) tuples
            
        Returns:
            List of unique Game objects with best odds
        """
        if not games_with_sources:
            return []
        
        # Group games by similarity
        game_groups = []
        
        for game, source in games_with_sources:
            # Find matching group
            matched = False
            for group in game_groups:
                if self._games_match(game, group[0][0]):
                    group.append((game, source))
                    matched = True
                    break
            
            if not matched:
                game_groups.append([(game, source)])
        
        # Merge each group and select best odds
        merged_games = []
        for group in game_groups:
            merged = self._merge_game_group(group)
            merged_games.append(merged)
        
        return merged_games
    
    def _games_match(self, game1: Game, game2: Game) -> bool:
        """Check if two games are the same using fuzzy matching.
        
        Args:
            game1: First game
            game2: Second game
            
        Returns:
            True if games match
        """
        # Compare team names with fuzzy matching
        home_similarity = fuzz.ratio(
            game1.home_team.lower(),
            game2.home_team.lower()
        )
        away_similarity = fuzz.ratio(
            game1.away_team.lower(),
            game2.away_team.lower()
        )
        
        # Check if teams match (>85% similar)
        teams_match = (home_similarity > self.fuzzy_threshold and 
                      away_similarity > self.fuzzy_threshold)
        
        # Could also check time difference, but for now just use team names
        return teams_match
    
    def _merge_game_group(self, group: List[tuple]) -> Game:
        """Merge multiple instances of the same game, selecting best odds.
        
        Args:
            group: List of (Game, source) tuples for the same game
            
        Returns:
            Merged Game object with best odds
        """
        # Use the first game as base
        base_game, base_source = group[0]
        
        # Find best odds across all sources
        best_home_odds = base_game.home_odds
        best_away_odds = base_game.away_odds
        best_home_source = base_source
        best_away_source = base_source
        
        for game, source in group[1:]:
            if game.home_odds and game.home_odds > best_home_odds:
                best_home_odds = game.home_odds
                best_home_source = source
            
            if game.away_odds and game.away_odds > best_away_odds:
                best_away_odds = game.away_odds
                best_away_source = source
        
        # Create merged game with best odds
        merged = Game(
            id=base_game.id,
            home_team=base_game.home_team,
            away_team=base_game.away_team,
            sport=base_game.sport,
            commence_time=base_game.commence_time,
            bookmaker=f"{best_home_source}/{best_away_source}",
            home_odds=best_home_odds,
            away_odds=best_away_odds,
            home_spread=base_game.home_spread,
            away_spread=base_game.away_spread,
            over_under=base_game.over_under,
            over_odds=base_game.over_odds,
            under_odds=base_game.under_odds
        )
        
        # Add metadata about sources
        if len(group) > 1:
            sources = [s for _, s in group]
            print(f"  ✓ Merged {base_game.home_team} vs {base_game.away_team} from {', '.join(sources)}")
            print(f"    Best odds: {best_home_odds} ({best_home_source}) / {best_away_odds} ({best_away_source})")
        
        return merged


# Test function
if __name__ == "__main__":
    print("Testing Odds Aggregator...")
    print("=" * 60)
    
    aggregator = OddsAggregator()
    games = aggregator.get_all_odds()
    
    print(f"\n📊 Results: {len(games)} unique games")
    print("=" * 60)
    
    if games:
        print("\nFirst 5 games:")
        for i, game in enumerate(games[:5], 1):
            print(f"\n{i}. {game.home_team} vs {game.away_team}")
            print(f"   Source: {game.bookmaker}")
            print(f"   Odds: {game.home_odds} / {game.away_odds}")
