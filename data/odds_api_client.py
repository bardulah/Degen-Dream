"""Enhanced OddsAPI client with retry logic, fallbacks, and smart league selection."""

import requests
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from config.settings import settings
from agents.base_agent import Game


class OddsAPIClientV2:
    """OddsAPI client with robust error handling and smart sport/league selection."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OddsAPI client.
        
        Args:
            api_key: TheOddsAPI key (defaults to settings)
        """
        self.api_key = api_key or settings.ODDS_API_KEY
        self.base_url = settings.ODDS_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (DegnenDream/1.0)"
        })
        
        # Track API health
        self.last_error_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.error_backoff_seconds = 60
        
        # Cache for league availability
        self.league_cache: Dict[str, Tuple[List[Game], datetime]] = {}
        self.cache_ttl_minutes = 30
        
        # API request tracking
        self.requests_made = 0
        self.requests_failed = 0
    
    def is_healthy(self) -> bool:
        """Check if API is considered healthy based on recent errors.
        
        Returns:
            True if API should be used, False if we're in backoff
        """
        if self.last_error_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self.last_error_time).total_seconds()
        if elapsed < self.error_backoff_seconds:
            return False
        
        # Reset error counter after backoff
        self.consecutive_errors = 0
        self.last_error_time = None
        return True
    
    def get_available_sports_with_games(self, hours_ahead: int = 24) -> List[str]:
        """Get list of sports that have games in the next N hours.
        
        Strategy: Query /sports endpoint, then for each sport check if it has games today.
        
        Args:
            hours_ahead: How many hours ahead to check
        
        Returns:
            List of sport keys that have games (e.g., ['soccer_epl', 'basketball_nba'])
        """
        if not self.api_key:
            return []
        
        sports_with_games = []
        
        try:
            # Get all available sports
            url = f"{self.base_url}/sports"
            params = {"apiKey": self.api_key}
            self.requests_made += 1
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            all_sports = response.json()
            now = datetime.utcnow()
            cutoff = now + timedelta(hours=hours_ahead)
            
            # For each sport, check if it has games
            for sport in all_sports:
                sport_key = sport["key"]
                
                # Skip inactive sports
                if not sport.get("active", True):
                    continue
                
                try:
                    # Quick check: get odds for this sport
                    odds_url = f"{self.base_url}/sports/{sport_key}/odds"
                    odds_params = {
                        "apiKey": self.api_key,
                        "regions": "eu,us",
                        "markets": "h2h",
                        "oddsFormat": "decimal"
                    }
                    self.requests_made += 1
                    odds_response = self.session.get(odds_url, params=odds_params, timeout=10)
                    
                    if odds_response.status_code == 200:
                        games_data = odds_response.json()
                        
                        # Check if any games have commence_time within our window
                        for game in games_data:
                            try:
                                game_time = datetime.fromisoformat(
                                    game["commence_time"].replace('Z', '+00:00')
                                )
                                if now <= game_time <= cutoff:
                                    sports_with_games.append(sport_key)
                                    break
                            except (ValueError, TypeError):
                                continue
                
                except Exception:
                    # Skip sports that error
                    continue
            
            return sports_with_games
        
        except Exception as e:
            print(f"  ⚠️  Error fetching available sports: {str(e)[:50]}")
            return []
    
    def get_odds_for_sport(self, sport_key: str, hours_ahead: int = 24, retry_count: int = 2) -> List[Game]:
        """Get odds for a specific sport, filtering for games within the next N hours.
        
        Args:
            sport_key: Sport key (e.g., 'soccer_epl', 'basketball_nba')
            hours_ahead: Only return games within next N hours
            retry_count: Number of retries on error
        
        Returns:
            List of Game objects for that sport
        """
        if not self.api_key:
            return []
        
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)
        
        # Try with retries
        for attempt in range(retry_count):
            try:
                url = f"{self.base_url}/sports/{sport_key}/odds"
                params = {
                    "apiKey": self.api_key,
                    "regions": "eu,us",
                    "markets": "h2h,spreads,totals",
                    "oddsFormat": "decimal"
                }
                
                self.requests_made += 1
                response = self.session.get(url, params=params, timeout=10)
                
                if response.status_code == 401:
                    self.requests_failed += 1
                    raise Exception("Unauthorized: Invalid or expired API key")
                elif response.status_code == 404:
                    self.requests_failed += 1
                    return []  # Sport not found, return empty
                elif response.status_code == 429:
                    self.requests_failed += 1
                    # Rate limited, wait and retry
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise Exception("Rate limited: Too many requests")
                
                response.raise_for_status()
                data = response.json()
                
                # Filter games for this time window
                games = []
                for event in data:
                    try:
                        game_time = datetime.fromisoformat(
                            event["commence_time"].replace('Z', '+00:00')
                        )
                        if not (now <= game_time <= cutoff):
                            continue
                        
                        if not event.get("bookmakers"):
                            continue
                        
                        bookmaker = event["bookmakers"][0]
                        h2h_market = self._find_market(bookmaker["markets"], "h2h")
                        spreads_market = self._find_market(bookmaker["markets"], "spreads")
                        totals_market = self._find_market(bookmaker["markets"], "totals")
                        
                        # Map sport key to sport name
                        sport_name = sport_key.split('_')[0]  # soccer_epl -> soccer
                        
                        game = Game(
                            id=event["id"],
                            home_team=event["home_team"],
                            away_team=event["away_team"],
                            sport=sport_name,
                            commence_time=event["commence_time"],
                            bookmaker=bookmaker["key"],
                            home_odds=self._get_team_odds(h2h_market, event["home_team"]),
                            away_odds=self._get_team_odds(h2h_market, event["away_team"]),
                            draw_odds=self._get_draw_odds(h2h_market),
                            home_spread=self._get_spread(spreads_market, event["home_team"]),
                            away_spread=self._get_spread(spreads_market, event["away_team"]),
                            over_under=self._get_total_line(totals_market),
                            over_odds=self._get_total_odds(totals_market, "Over"),
                            under_odds=self._get_total_odds(totals_market, "Under")
                        )
                        games.append(game)
                    
                    except Exception:
                        continue
                
                return games
            
            except Exception as e:
                self.consecutive_errors += 1
                self.last_error_time = datetime.utcnow()
                
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        print(f"  🔴 OddsAPI health degraded, entering {self.error_backoff_seconds}s backoff")
                    raise
        
        return []
    

    
    def _find_market(self, markets: List[Dict], market_key: str) -> Optional[Dict]:
        """Find a specific market in the markets list."""
        for market in markets:
            if market["key"] == market_key:
                return market
        return None
    
    def _get_team_odds(self, market: Optional[Dict], team: str) -> float:
        """Get odds for a specific team."""
        if not market or "outcomes" not in market:
            return 1.91
        for outcome in market["outcomes"]:
            if outcome["name"] == team:
                return outcome.get("price", 1.91)
        return 1.91
    
    def _get_draw_odds(self, market: Optional[Dict]) -> Optional[float]:
        """Get odds for draw in 3-way market."""
        if not market or "outcomes" not in market:
            return None
        for outcome in market["outcomes"]:
            if outcome["name"].lower() == "draw":
                return outcome.get("price")
        return None
    
    def _get_spread(self, market: Optional[Dict], team: str) -> Optional[float]:
        """Get spread for a specific team."""
        if not market or "outcomes" not in market:
            return None
        for outcome in market["outcomes"]:
            if outcome["name"] == team:
                return outcome.get("point")
        return None
    
    def _get_total_line(self, market: Optional[Dict]) -> Optional[float]:
        """Get total line (over/under)."""
        if not market or "outcomes" not in market:
            return None
        if market["outcomes"]:
            return market["outcomes"][0].get("point")
        return None
    
    def _get_total_odds(self, market: Optional[Dict], side: str) -> Optional[float]:
        """Get odds for over or under."""
        if not market or "outcomes" not in market:
            return None
        for outcome in market["outcomes"]:
            if outcome["name"] == side:
                return outcome.get("price")
        return None
    
    def _get_from_cache(self, league_key: str) -> Optional[List[Game]]:
        """Get cached results if fresh."""
        if league_key not in self.league_cache:
            return None
        
        games, cached_time = self.league_cache[league_key]
        age_minutes = (datetime.utcnow() - cached_time).total_seconds() / 60
        
        if age_minutes > self.cache_ttl_minutes:
            del self.league_cache[league_key]
            return None
        
        return games
    
    def _cache_result(self, league_key: str, games: List[Game]) -> None:
        """Cache league results."""
        self.league_cache[league_key] = (games, datetime.utcnow())
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API statistics."""
        return {
            "requests_made": self.requests_made,
            "requests_failed": self.requests_failed,
            "success_rate": round(
                100 * (self.requests_made - self.requests_failed) / max(1, self.requests_made),
                1
            ),
            "consecutive_errors": self.consecutive_errors,
            "is_healthy": self.is_healthy(),
            "cached_leagues": len(self.league_cache)
        }
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        self.league_cache.clear()


# Backward compatibility alias
OddsAPIClient = OddsAPIClientV2
