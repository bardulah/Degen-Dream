"""Fetch real match scores from various sources."""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from agents.base_agent import Game
import os
from fuzzywuzzy import fuzz


class ScoresFetcher:
    """Fetches real match scores from various sources."""
    
    def __init__(self):
        """Initialize scores fetcher."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def fetch_today_scores(self, sport: str = "soccer") -> List[Game]:
        """Fetch today's match scores.
        
        Args:
            sport: Sport type (soccer, basketball, hockey, tennis)
        
        Returns:
            List of Game objects with scores (home_score, away_score)
        """
        # Try sources in order of preference
        scores = []
        
        # 1. Try free API-Football (has live scores)
        if sport == "soccer":
            scores = self._fetch_from_api_football(sport)
            if scores:
                return scores
        
        # 2. Try OddsAPI (has scores in in-play markets)
        scores = self._fetch_from_odds_api(sport)
        if scores:
            return scores
        
        # 3. Try ESPN (has more sports)
        scores = self._fetch_from_espn(sport)
        if scores:
            return scores
        
        # 4. Try Flashscore (most reliable but needs JS)
        # scores = self._fetch_from_flashscore(sport)
        # if scores:
        #     return scores
        
        print(f"⚠️  Could not fetch scores for {sport}")
        return []
    
    def fetch_historical_scores(self, date: datetime, sport: str = "soccer") -> List[Game]:
        """Fetch match scores for a specific date.
        
        Args:
            date: Date to fetch scores for
            sport: Sport type
        
        Returns:
            List of Game objects with scores
        """
        # Format date
        date_str = date.strftime("%Y-%m-%d")
        
        # Try sources
        scores = self._fetch_from_espn_date(sport, date_str)
        if scores:
            return scores
        
        return []
    
    def _fetch_from_api_football(self, sport: str) -> List[Game]:
        """Fetch scores from free API-Football.
        
        Uses rapid-api.io free tier (no key required for basic requests).
        
        Args:
            sport: Sport type (only soccer supported)
        
        Returns:
            List of Game objects with scores
        """
        try:
            if sport != "soccer":
                return []
            
            # Today's date
            today = datetime.now().strftime("%Y-%m-%d")
            
            # API-Football endpoint for today's matches
            url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
            params = {
                "date": today,
                "status": "FT"  # FT = Finished, also includes LV (Live)
            }
            
            headers = {
                "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", ""),
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
            }
            
            print(f"  📡 Fetching scores from API-Football ({sport})...")
            
            # If no RapidAPI key, skip
            if not headers["X-RapidAPI-Key"]:
                print(f"    ℹ️  API-Football requires RAPIDAPI_KEY env var")
                return []
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"    ❌ API-Football error: {response.status_code}")
                return []
            
            data = response.json()
            games = []
            
            for match in data.get("response", []):
                try:
                    # Only include finished matches (with final scores)
                    if match.get("fixture", {}).get("status", {}).get("short") not in ["FT", "AET", "PEN"]:
                        continue
                    
                    game = Game(
                        id=f"apifootball_{match['fixture']['id']}",
                        home_team=match.get("teams", {}).get("home", {}).get("name", "Unknown"),
                        away_team=match.get("teams", {}).get("away", {}).get("name", "Unknown"),
                        sport=sport,
                        league=match.get("league", {}).get("name", "unknown"),
                        commence_time=match.get("fixture", {}).get("date", datetime.now().isoformat()),
                        bookmaker="api_football",
                        home_odds=1.0,  # Not available in this API
                        away_odds=1.0,
                        home_score=match.get("goals", {}).get("home"),
                        away_score=match.get("goals", {}).get("away"),
                    )
                    
                    # Only include if we have scores
                    if game.home_score is not None and game.away_score is not None:
                        games.append(game)
                
                except Exception as e:
                    continue
            
            if games:
                print(f"    ✅ Found {len(games)} finished matches")
            else:
                print(f"    ℹ️  No finished matches found")
            
            return games
            
        except Exception as e:
            print(f"    ⚠️  API-Football error: {str(e)[:50]}")
            return []
    
    def _fetch_from_odds_api(self, sport: str) -> List[Game]:
        """Fetch scores from TheOddsAPI.
        
        TheOddsAPI in-play markets include live scores.
        
        Args:
            sport: Sport type
        
        Returns:
            List of Game objects with scores
        """
        try:
            api_key = os.getenv("ODDS_API_KEY")
            if not api_key:
                return []
            
            # Map sports to OddsAPI format
            sport_map = {
                "soccer": "soccer",
                "basketball": "basketball",
                "hockey": "ice_hockey",
                "tennis": "tennis",
            }
            
            odds_sport = sport_map.get(sport)
            if not odds_sport:
                return []
            
            # Get in-play (live) markets which have scores
            url = f"https://api.the-odds-api.com/v4/sports/{odds_sport}/scores"
            params = {
                "apiKey": api_key,
                "daysFrom": 0,  # Today only
                "oddsFormat": "decimal"
            }
            
            print(f"  📡 Fetching scores from TheOddsAPI ({sport})...")
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"    ❌ OddsAPI error: {response.status_code}")
                return []
            
            data = response.json()
            games = []
            
            for match in data.get("scores", []):
                try:
                    game = Game(
                        id=match.get("id", f"odds_{len(games)}"),
                        home_team=match.get("home_team", "Unknown"),
                        away_team=match.get("away_team", "Unknown"),
                        sport=sport,
                        league=match.get("league_name", "unknown"),
                        commence_time=match.get("commence_time", datetime.now().isoformat()),
                        bookmaker="odds_api",
                        home_odds=1.0,  # Not in scores endpoint
                        away_odds=1.0,
                        home_score=match.get("scores", [{}])[0].get("score") if match.get("scores") else None,
                        away_score=match.get("scores", [{}])[-1].get("score") if match.get("scores") and len(match.get("scores", [])) > 1 else None,
                    )
                    
                    # Only include if we have scores
                    if game.home_score is not None and game.away_score is not None:
                        games.append(game)
                
                except Exception as e:
                    continue
            
            if games:
                print(f"    ✅ Found {len(games)} games with scores")
            
            return games
            
        except Exception as e:
            print(f"    ⚠️  OddsAPI error: {str(e)[:50]}")
            return []
    
    def _fetch_from_espn(self, sport: str) -> List[Game]:
        """Fetch scores from ESPN.
        
        ESPN has comprehensive sports coverage and live scores.
        
        Args:
            sport: Sport type
        
        Returns:
            List of Game objects with scores
        """
        try:
            # ESPN URLs by sport
            espn_urls = {
                "soccer": "https://www.espn.com/soccer/schedule",
                "basketball": "https://www.espn.com/nba/scoreboard",
                "hockey": "https://www.espn.com/nhl/scoreboard",
                "tennis": "https://www.espn.com/tennis/schedule",
            }
            
            url = espn_urls.get(sport)
            if not url:
                return []
            
            print(f"  📡 Fetching scores from ESPN ({sport})...")
            
            # ESPN requires JavaScript rendering - would need Playwright
            # For now, return empty - this is a placeholder
            print(f"    ℹ️  ESPN fetching requires JavaScript rendering (not yet implemented)")
            
            return []
            
        except Exception as e:
            print(f"    ⚠️  ESPN error: {str(e)[:50]}")
            return []
    
    def _fetch_from_espn_date(self, sport: str, date_str: str) -> List[Game]:
        """Fetch scores from ESPN for specific date.
        
        Args:
            sport: Sport type
            date_str: Date string in YYYY-MM-DD format
        
        Returns:
            List of Game objects with scores
        """
        # Same as _fetch_from_espn for now
        # Would need JavaScript rendering for ESPN
        return []
    
    def _fetch_from_flashscore(self, sport: str) -> List[Game]:
        """Fetch scores from Flashscore.
        
        Flashscore has comprehensive live scores.
        
        Args:
            sport: Sport type
        
        Returns:
            List of Game objects with scores
        """
        try:
            # Flashscore requires JavaScript rendering
            # Would need Playwright + flashscore-scraper.js
            
            print(f"  📡 Fetching scores from Flashscore ({sport})...")
            print(f"    ℹ️  Flashscore fetching requires JavaScript rendering (not yet implemented)")
            
            return []
            
        except Exception as e:
            print(f"    ⚠️  Flashscore error: {str(e)[:50]}")
            return []
    
    def get_match_score(self, home_team: str, away_team: str, sport: str = "soccer") -> Optional[tuple]:
        """Get score for a specific match.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            sport: Sport type
        
        Returns:
            Tuple of (home_score, away_score) or None
        """
        scores = self.fetch_today_scores(sport)
        
        # Normalize team names
        home_norm = home_team.lower().strip()
        away_norm = away_team.lower().strip()
        
        for game in scores:
            if (home_norm in game.home_team.lower() or game.home_team.lower() in home_norm) and \
               (away_norm in game.away_team.lower() or game.away_team.lower() in away_norm):
                return (game.home_score, game.away_score)
        
        return None
    
    def match_bets_with_scores(self, bets: List[Dict[str, Any]], sport: str = "soccer") -> List[Dict[str, Any]]:
        """Match bets with their scores.
        
        Args:
            bets: List of bet dictionaries with home_team, away_team
            sport: Sport type
        
        Returns:
            List of bets with added score information
        """
        scores = self.fetch_today_scores(sport)
        
        for bet in bets:
            # Find matching score
            score = self.get_match_score(
                bet["home_team"],
                bet["away_team"],
                sport
            )
            
            if score:
                bet["home_score"] = score[0]
                bet["away_score"] = score[1]
            else:
                bet["home_score"] = None
                bet["away_score"] = None
        
        return bets


class MockScoresFetcher(ScoresFetcher):
    """Mock scores fetcher for testing."""
    
    def fetch_today_scores(self, sport: str = "soccer") -> List[Game]:
        """Return mock scores for testing.
        
        Args:
            sport: Sport type
        
        Returns:
            List of mock Game objects with scores
        """
        mock_games = [
            # Soccer matches
            Game(
                id="mock_1",
                home_team="Real Madrid",
                away_team="Barcelona",
                sport="soccer",
                league="la_liga",
                commence_time=datetime.now().isoformat(),
                bookmaker="mock",
                home_odds=2.4,
                away_odds=2.8,
                home_score=1,
                away_score=2,
            ),
            Game(
                id="mock_2",
                home_team="Manchester City",
                away_team="Liverpool",
                sport="soccer",
                league="epl",
                commence_time=datetime.now().isoformat(),
                bookmaker="mock",
                home_odds=1.8,
                away_odds=2.1,
                home_score=3,
                away_score=2,
            ),
            Game(
                id="mock_3",
                home_team="Arsenal",
                away_team="Chelsea",
                sport="soccer",
                league="epl",
                commence_time=datetime.now().isoformat(),
                bookmaker="mock",
                home_odds=2.0,
                away_odds=1.9,
                home_score=1,
                away_score=1,
            ),
            # Basketball matches
            Game(
                id="mock_4",
                home_team="Los Angeles Lakers",
                away_team="Golden State Warriors",
                sport="basketball",
                league="nba",
                commence_time=datetime.now().isoformat(),
                bookmaker="mock",
                home_odds=2.1,
                away_odds=1.8,
                home_score=120,
                away_score=115,
            ),
            Game(
                id="mock_5",
                home_team="Boston Celtics",
                away_team="Miami Heat",
                sport="basketball",
                league="nba",
                commence_time=datetime.now().isoformat(),
                bookmaker="mock",
                home_odds=1.9,
                away_odds=1.95,
                home_score=105,
                away_score=98,
            ),
        ]
        
        return mock_games
