"""
Sports Score Fetcher - Simple implementation using ESPN's Hidden API

This script demonstrates how to fetch finished match scores for:
- NBA (Basketball)
- NHL (Hockey)
- Soccer (EPL, MLS, La Liga, etc.)

No authentication required, no scraping, just clean JSON API calls.

Usage:
    python sports_score_fetcher.py

Requirements:
    pip install requests
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict
import time


class SportsScoreFetcher:
    """Fetch finished sports scores using ESPN's unofficial API."""

    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"

    # Soccer league codes
    SOCCER_LEAGUES = {
        'EPL': 'eng.1',         # English Premier League
        'MLS': 'usa.1',         # Major League Soccer
        'LA_LIGA': 'esp.1',     # Spanish La Liga
        'BUNDESLIGA': 'ger.1',  # German Bundesliga
        'SERIE_A': 'ita.1',     # Italian Serie A
        'LIGUE_1': 'fra.1',     # French Ligue 1
        'UCL': 'uefa.champions' # UEFA Champions League
    }

    def __init__(self):
        """Initialize the fetcher with a requests session."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def _get_scoreboard(self, sport: str, league: str, date_str: str) -> Dict:
        """
        Generic scoreboard fetcher.

        Args:
            sport: Sport type (e.g., 'basketball', 'hockey', 'soccer')
            league: League code (e.g., 'nba', 'nhl', 'eng.1')
            date_str: Date in YYYYMMDD format

        Returns:
            JSON response from ESPN API
        """
        url = f"{self.BASE_URL}/{sport}/{league}/scoreboard"
        params = {'dates': date_str}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return {'events': []}

    def _parse_finished_games(self, data: Dict) -> List[Dict]:
        """
        Parse finished games from ESPN API response.

        Args:
            data: JSON response from ESPN API

        Returns:
            List of finished game dictionaries
        """
        finished_games = []

        for event in data.get('events', []):
            # Only get completed games
            if not event.get('status', {}).get('type', {}).get('completed', False):
                continue

            try:
                competition = event['competitions'][0]
                competitors = competition['competitors']

                # Find home and away teams
                home = next((c for c in competitors if c.get('homeAway') == 'home'), None)
                away = next((c for c in competitors if c.get('homeAway') == 'away'), None)

                if not home or not away:
                    continue

                home_score = int(home.get('score', 0))
                away_score = int(away.get('score', 0))

                game_info = {
                    'game_id': event['id'],
                    'date': event.get('date', ''),
                    'status': event.get('status', {}).get('type', {}).get('detail', 'Final'),
                    'home_team': home['team']['displayName'],
                    'home_abbr': home['team'].get('abbreviation', ''),
                    'away_team': away['team']['displayName'],
                    'away_abbr': away['team'].get('abbreviation', ''),
                    'home_score': home_score,
                    'away_score': away_score,
                    'winner': home['team']['displayName'] if home_score > away_score else (
                        away['team']['displayName'] if away_score > home_score else 'TIE'
                    )
                }
                finished_games.append(game_info)

            except (KeyError, IndexError, ValueError) as e:
                print(f"Error parsing game: {e}")
                continue

        return finished_games

    def get_nba_scores(self, date_str: str) -> List[Dict]:
        """
        Get NBA finished games for a specific date.

        Args:
            date_str: Date in YYYYMMDD format (e.g., '20250115')

        Returns:
            List of finished NBA games
        """
        data = self._get_scoreboard('basketball', 'nba', date_str)
        return self._parse_finished_games(data)

    def get_nhl_scores(self, date_str: str) -> List[Dict]:
        """
        Get NHL finished games for a specific date.

        Args:
            date_str: Date in YYYYMMDD format (e.g., '20250115')

        Returns:
            List of finished NHL games
        """
        data = self._get_scoreboard('hockey', 'nhl', date_str)
        return self._parse_finished_games(data)

    def get_soccer_scores(self, league_code: str, date_str: str) -> List[Dict]:
        """
        Get soccer finished games for a specific league and date.

        Args:
            league_code: League code (e.g., 'eng.1' for EPL)
                        Use SOCCER_LEAGUES dict for common leagues
            date_str: Date in YYYYMMDD format

        Returns:
            List of finished soccer games
        """
        data = self._get_scoreboard('soccer', league_code, date_str)
        return self._parse_finished_games(data)

    def get_all_scores(self, date_str: str, soccer_leagues: List[str] = None) -> Dict[str, List[Dict]]:
        """
        Get all scores across sports for a specific date.

        Args:
            date_str: Date in YYYYMMDD format
            soccer_leagues: List of soccer league codes to fetch (default: EPL and MLS)

        Returns:
            Dictionary with scores for each sport
        """
        if soccer_leagues is None:
            soccer_leagues = ['eng.1', 'usa.1']  # EPL and MLS by default

        all_scores = {
            'nba': self.get_nba_scores(date_str),
            'nhl': self.get_nhl_scores(date_str),
            'soccer': {}
        }

        # Add small delay to be respectful
        time.sleep(1)

        # Fetch soccer leagues
        for league in soccer_leagues:
            league_name = next((k for k, v in self.SOCCER_LEAGUES.items() if v == league), league)
            all_scores['soccer'][league_name] = self.get_soccer_scores(league, date_str)
            time.sleep(0.5)  # Small delay between requests

        return all_scores


def format_game(game: Dict) -> str:
    """Format a game dictionary into a readable string."""
    return (
        f"{game['away_abbr'] if game.get('away_abbr') else game['away_team']:15} "
        f"{game['away_score']:3} @ "
        f"{game['home_abbr'] if game.get('home_abbr') else game['home_team']:15} "
        f"{game['home_score']:3} - {game['status']}"
    )


def main():
    """Example usage of the SportsScoreFetcher."""

    # Initialize fetcher
    fetcher = SportsScoreFetcher()

    # Get yesterday's date (finished games)
    # Note: Adjust this date to a recent past date if system date is incorrect
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

    # For testing, use a known date with games (e.g., November 26, 2024)
    # yesterday = '20241126'

    print(f"Fetching scores for: {yesterday}\n")

    # Fetch NBA scores
    print("=" * 70)
    print("NBA GAMES")
    print("=" * 70)
    nba_games = fetcher.get_nba_scores(yesterday)
    if nba_games:
        for game in nba_games:
            print(format_game(game))
    else:
        print("No finished NBA games found.")
    print()

    time.sleep(1)  # Be respectful with requests

    # Fetch NHL scores
    print("=" * 70)
    print("NHL GAMES")
    print("=" * 70)
    nhl_games = fetcher.get_nhl_scores(yesterday)
    if nhl_games:
        for game in nhl_games:
            print(format_game(game))
    else:
        print("No finished NHL games found.")
    print()

    time.sleep(1)

    # Fetch Premier League scores
    print("=" * 70)
    print("PREMIER LEAGUE GAMES")
    print("=" * 70)
    epl_games = fetcher.get_soccer_scores('eng.1', yesterday)
    if epl_games:
        for game in epl_games:
            print(format_game(game))
    else:
        print("No finished Premier League games found.")
    print()

    # Example: Get all scores at once
    print("=" * 70)
    print("ALL SCORES (Alternative Method)")
    print("=" * 70)
    all_scores = fetcher.get_all_scores(yesterday, soccer_leagues=['eng.1', 'esp.1'])

    print(f"\nNBA: {len(all_scores['nba'])} games")
    print(f"NHL: {len(all_scores['nhl'])} games")
    for league, games in all_scores['soccer'].items():
        print(f"{league}: {len(games)} games")


if __name__ == '__main__':
    main()
