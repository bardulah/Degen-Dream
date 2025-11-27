"""Web scrapers for betting sites like Niké."""

import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime
import random
from agents.base_agent import Game


class NikeScraper:
    """Scraper for Niké betting (Slovak betting site) - multi-sport support."""

    # Map sport names to Nike.sk URLs
    SPORTS_MAP = {
        "soccer": "futbal",
        "hockey": "hokej",
        "basketball": "basketbal",
        "tennis": "tenis",
        "american_football": "americanfootball",
        "baseball": "baseball",
        "handball": "zalmova",
        "volleyball": "volejbal",
    }
    


    def __init__(self):
        """Initialize Niké scraper."""
        self.base_url = "https://www.nike.sk"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _get_default_league(self, sport: str) -> str:
        """Get default league name when data-tournament attribute is missing.
        
        Args:
            sport: Sport type
        
        Returns:
            Generic league name for fallback
        """
        sport_defaults = {
            "soccer": "unknown_soccer",
            "hockey": "unknown_hockey",
            "basketball": "unknown_basketball",
            "tennis": "unknown_tennis",
            "american_football": "unknown_american_football",
            "baseball": "unknown_baseball",
            "handball": "unknown_handball",
            "volleyball": "unknown_volleyball",
        }
        return sport_defaults.get(sport, "unknown")
    
    def get_odds(self, sport: str = "soccer") -> List[Game]:
        """Scrape odds from Nike.sk for a specific sport.
        
        Args:
            sport: Sport to get odds for (soccer, hockey, basketball, etc.)
            
        Returns:
            List of Game objects with odds
        """
        nike_sport = self.SPORTS_MAP.get(sport)
        if not nike_sport:
            print(f"Unsupported sport: {sport}")
            return []
        
        url = f"{self.base_url}/tipovanie/{nike_sport}"
        return self._scrape_sport_page(url, sport)
    
    def get_all_sports(self) -> Dict[str, List[Game]]:
        """Scrape all available sports from Nike.sk.
        
        Returns:
            Dict mapping sport name to list of games
        """
        all_games = {}
        
        for sport_name, nike_sport in self.SPORTS_MAP.items():
            url = f"{self.base_url}/tipovanie/{nike_sport}"
            try:
                games = self._scrape_sport_page(url, sport_name)
                if games:
                    all_games[sport_name] = games
                    print(f"  ✅ {sport_name}: {len(games)} games")
                else:
                    print(f"  ℹ️  {sport_name}: No games today")
            except Exception as e:
                print(f"  ⚠️  {sport_name}: Failed ({str(e)[:30]})")
        
        return all_games
    
    def _scrape_sport_page(self, url: str, sport: str) -> List[Game]:
        """Scrape a single sport page from Nike.sk.
        
        Args:
            url: Full URL to the sport page
            sport: Sport name for Game objects
            
        Returns:
            List of Game objects
        """
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to the sport page
                page.goto(url, timeout=30000)
                
                # Handle cookie consent if present
                try:
                    page.get_by_text('Povoliť všetko').click(timeout=5000)
                except Exception:
                    pass  # Cookie banner not present or already accepted
                
                # Wait for the main content to load
                page.wait_for_selector('div.native-scroll', timeout=15000)
                
                games = []
                
                # Find all game rows
                game_rows = page.locator('div.bet-view-prematch-row').all()
                
                for row in game_rows:
                    try:
                        # Extract team names from the opponents button
                        opponents_btn = row.locator('button.bets-opponents').first
                        if opponents_btn.count() == 0:
                            continue
                        
                        # Get team divs within the button
                        team_divs = opponents_btn.locator('div').all()
                        if len(team_divs) < 2:
                            continue
                        
                        # First and last divs are the teams (middle is 'vs')
                        home_team = team_divs[0].inner_text().strip()
                        away_team = team_divs[-1].inner_text().strip()
                        
                        if not home_team or not away_team:
                            continue
                        
                        # Extract odds - look for bet-box links with odds
                        odd_elements = row.locator('a.bet-box span[data-atid="n1-bet-odd"]').all()
                        
                        if len(odd_elements) < 2:
                            continue
                        
                        # Get the first 2 odds (at minimum for sports without draws)
                        try:
                            home_odds = float(odd_elements[0].inner_text().strip())
                            # If 3+ odds exist, second is draw, third is away
                            # If only 2, second is away (no draw)
                            if len(odd_elements) >= 3:
                                draw_odds = float(odd_elements[1].inner_text().strip())
                                away_odds = float(odd_elements[2].inner_text().strip())
                            else:
                                draw_odds = None
                                away_odds = float(odd_elements[1].inner_text().strip())
                        except (ValueError, IndexError):
                            continue
                        
                        # Extract match ID from data attributes if available
                        match_id_attr = row.locator('.bet-table-left').first.get_attribute('data-match-id')
                        match_id = match_id_attr if match_id_attr else f"nike_{len(games)}"
                        
                        # Extract league from data-tournament attribute
                        league = row.locator('.bet-table-left').first.get_attribute('data-tournament')
                        if not league:
                            # Fallback to generic default if data-tournament not available
                            league = self._get_default_league(sport)
                        
                        # Create Game object
                        game = Game(
                            id=match_id,
                            home_team=home_team,
                            away_team=away_team,
                            sport=sport,
                            league=league,
                            commence_time=datetime.now().isoformat(),
                            bookmaker="nike_sk",
                            home_odds=home_odds,
                            away_odds=away_odds,
                            draw_odds=draw_odds  # None for non-draw sports
                        )
                        
                        games.append(game)
                        
                    except Exception as e:
                        # Skip games that fail to parse
                        continue
                
                browser.close()
                
                return games
                
        except Exception as e:
            print(f"Error scraping Nike.sk {sport}: {e}")
            return []

    def _get_simulated_nike_data(self) -> List[Dict[str, Any]]:
        """Generate simulated Niké betting data with "insider" info.

        Returns:
            Simulated betting data
        """
        return [
            {
                "game": "Slovan Bratislava vs Spartak Trnava",
                "sport": "futbal",
                "home_odds": 1.65,
                "away_odds": 4.2,
                "draw_odds": 3.5,
                "public_betting": {
                    "home": 78,  # 78% of bets on home
                    "away": 12,
                    "draw": 10
                },
                "insider_notes": "Heavy public money on Slovan. Sharp action on Trnava +1.5.",
                "line_movement": "Opened -1.5, now -1.0 (reverse line movement)",
                "timestamp": datetime.now().isoformat()
            },
            {
                "game": "ŽP Šport Podbrezová vs MFK Ružomberok",
                "sport": "futbal",
                "home_odds": 2.1,
                "away_odds": 3.2,
                "draw_odds": 3.1,
                "public_betting": {
                    "home": 45,
                    "away": 35,
                    "draw": 20
                },
                "insider_notes": "Balanced action. Weather could be factor (rain expected).",
                "line_movement": "Stable at -0.5",
                "timestamp": datetime.now().isoformat()
            }
        ]

    def get_public_betting_percentages(self, game_id: str) -> Dict[str, float]:
        """Get public betting percentages for a game.

        Args:
            game_id: Game identifier

        Returns:
            Public betting percentages
        """
        # Simulated public betting data
        return {
            "home": random.uniform(40, 80),
            "away": random.uniform(10, 40),
            "draw": random.uniform(5, 20)
        }

    def get_line_movements(self, game_id: str) -> List[Dict[str, Any]]:
        """Get historical line movements for a game.

        Args:
            game_id: Game identifier

        Returns:
            Line movement history
        """
        # Simulated line movement data
        return [
            {
                "time": "2024-01-20 09:00",
                "line": -1.5,
                "odds": -110
            },
            {
                "time": "2024-01-20 12:00",
                "line": -1.5,
                "odds": -105
            },
            {
                "time": "2024-01-20 15:00",
                "line": -1.0,
                "odds": -110
            }
        ]


class ComprehensiveScraper:
    """Aggregates data from multiple betting sites."""

    def __init__(self):
        """Initialize comprehensive scraper."""
        self.nike_scraper = NikeScraper()
        self.sources = ["nike", "tipos", "fortuna"]  # Slovak betting sites

    def get_best_lines(self, game: str) -> Dict[str, Any]:
        """Find best lines across multiple books.

        Args:
            game: Game identifier

        Returns:
            Best available lines
        """
        # In production, this would scrape multiple sites
        # For now, return sample data
        return {
            "best_home_odds": -105,
            "best_away_odds": +115,
            "books": {
                "nike": {"home": -110, "away": +110},
                "tipos": {"home": -105, "away": +105},
                "fortuna": {"home": -108, "away": +115}
            }
        }

    def detect_arbitrage(self) -> List[Dict[str, Any]]:
        """Detect arbitrage opportunities across books.

        Returns:
            List of arb opportunities
        """
        # Placeholder for arb detection
        return [
            {
                "game": "Sample Game",
                "book1": "nike",
                "bet1": "home",
                "odds1": -105,
                "book2": "tipos",
                "bet2": "away",
                "odds2": +120,
                "profit_margin": 1.8  # 1.8% guaranteed profit
            }
        ]
