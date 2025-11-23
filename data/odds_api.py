"""TheOddsAPI integration for real-time sports betting odds."""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from config.settings import settings
from agents.base_agent import Game


class OddsAPIClient:
    """Client for TheOddsAPI - real-time sports betting odds."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OddsAPI client.

        Args:
            api_key: TheOddsAPI key (defaults to settings)
        """
        self.api_key = api_key or settings.ODDS_API_KEY
        self.base_url = settings.ODDS_API_BASE_URL
        self.session = requests.Session()

    def get_sports(self) -> List[Dict[str, Any]]:
        """Get list of available sports.

        Returns:
            List of sports with keys and details
        """
        url = f"{self.base_url}/sports"
        params = {"apiKey": self.api_key}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching sports: {e}")
            return []

    def get_odds(
        self,
        sport: str = "soccer_epl",
        regions: str = "eu",
        markets: str = "h2h,spreads,totals",
        odds_format: str = "american"
    ) -> List[Game]:
        """Get odds for a specific sport.

        Args:
            sport: Sport key (e.g., 'soccer_epl', 'basketball_nba')
            regions: Regions for odds (us, uk, eu, au)
            markets: Markets to include (h2h, spreads, totals)
            odds_format: american or decimal

        Returns:
            List of Game objects with odds
        """
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return self._parse_odds_response(data)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds: {e}")
            return []

    def get_pinnacle_odds(self, sport: str = "soccer_epl") -> List[Game]:
        """Get Pinnacle odds specifically (sharpest book).

        Args:
            sport: Sport key

        Returns:
            List of Game objects with Pinnacle odds
        """
        # Pinnacle is often not available in TheOddsAPI free tier
        # This is a fallback that tries to get it
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "bookmakers": "pinnacle"
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return self._parse_odds_response(data)

        except requests.exceptions.RequestException as e:
            print(f"Pinnacle odds not available: {e}")
            return []

    def _parse_odds_response(self, data: List[Dict[str, Any]]) -> List[Game]:
        """Parse API response into Game objects.

        Args:
            data: Raw API response

        Returns:
            List of Game objects
        """
        games = []

        for event in data:
            try:
                # Get first bookmaker for simplicity
                if not event.get("bookmakers"):
                    continue

                bookmaker = event["bookmakers"][0]
                bookmaker_name = bookmaker["key"]

                # Parse markets
                h2h_market = self._find_market(bookmaker["markets"], "h2h")
                spreads_market = self._find_market(bookmaker["markets"], "spreads")
                totals_market = self._find_market(bookmaker["markets"], "totals")

                # Create Game object
                game = Game(
                    id=event["id"],
                    home_team=event["home_team"],
                    away_team=event["away_team"],
                    sport=event["sport_key"],
                    commence_time=event["commence_time"],
                    bookmaker=bookmaker_name,
                    home_odds=self._get_team_odds(h2h_market, event["home_team"]),
                    away_odds=self._get_team_odds(h2h_market, event["away_team"]),
                    home_spread=self._get_spread(spreads_market, event["home_team"]),
                    away_spread=self._get_spread(spreads_market, event["away_team"]),
                    over_under=self._get_total_line(totals_market),
                    over_odds=self._get_total_odds(totals_market, "Over"),
                    under_odds=self._get_total_odds(totals_market, "Under")
                )

                games.append(game)

            except Exception as e:
                print(f"Error parsing game: {e}")
                continue

        return games

    def _find_market(self, markets: List[Dict], market_key: str) -> Optional[Dict]:
        """Find a specific market in the markets list."""
        for market in markets:
            if market["key"] == market_key:
                return market
        return None

    def _get_team_odds(self, market: Optional[Dict], team: str) -> float:
        """Get odds for a specific team in h2h market."""
        if not market or "outcomes" not in market:
            return -110  # Default

        for outcome in market["outcomes"]:
            if outcome["name"] == team:
                return outcome.get("price", -110)

        return -110

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

    def get_sample_games(self) -> List[Game]:
        """Get sample games for testing (no API call).

        Returns:
            List of sample Game objects
        """
        return [
            Game(
                id="sample_001",
                home_team="Real Madrid",
                away_team="Barcelona",
                sport="soccer_spain_la_liga",
                commence_time=datetime.now().isoformat(),
                bookmaker="draftkings",
                home_odds=150,
                away_odds=180,
                home_spread=-1.5,
                away_spread=1.5,
                over_under=2.5,
                over_odds=-115,
                under_odds=-105
            ),
            Game(
                id="sample_002",
                home_team="Lakers",
                away_team="Warriors",
                sport="basketball_nba",
                commence_time=datetime.now().isoformat(),
                bookmaker="fanduel",
                home_odds=-120,
                away_odds=100,
                home_spread=-3.5,
                away_spread=3.5,
                over_under=225.5,
                over_odds=-110,
                under_odds=-110
            ),
            Game(
                id="sample_003",
                home_team="Slovan Bratislava",
                away_team="Spartak Trnava",
                sport="soccer_slovakia_super_liga",
                commence_time=datetime.now().isoformat(),
                bookmaker="nike",
                home_odds=-150,
                away_odds=350,
                home_spread=-1.5,
                away_spread=1.5,
                over_under=2.5,
                over_odds=105,
                under_odds=-125
            )
        ]
