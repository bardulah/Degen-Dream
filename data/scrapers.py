"""Web scrapers for betting sites like Niké."""

import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime
import random
from agents.base_agent import Game


class NikeScraper:
    """Scraper for Niké betting (Slovak betting site)."""

    def __init__(self):
        """Initialize Niké scraper."""
        self.base_url = "https://www.nike.sk"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })


    def get_odds(self, sport: str = "soccer") -> List[Game]:
        """Scrape odds from Nike.sk
        
        Args:
            sport: Sport to get odds for (default: soccer)
            
        Returns:
            List of Game objects with odds
        """
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to the football betting page
                page.goto('https://www.nike.sk/tipovanie/futbal', timeout=30000)
                
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
                        
                        if len(odd_elements) < 3:
                            continue
                        
                        # Get the first 3 odds (1, X, 2)
                        try:
                            home_odds = float(odd_elements[0].inner_text().strip())
                            draw_odds = float(odd_elements[1].inner_text().strip())
                            away_odds = float(odd_elements[2].inner_text().strip())
                        except (ValueError, IndexError):
                            continue
                        
                        # Extract match ID from data attributes if available
                        match_id_attr = row.locator('.bet-table-left').first.get_attribute('data-match-id')
                        match_id = match_id_attr if match_id_attr else f"nike_{len(games)}"
                        
                        # Create Game object using the base_agent.Game structure
                        game = Game(
                            id=match_id,
                            home_team=home_team,
                            away_team=away_team,
                            sport="soccer",
                            commence_time=datetime.now().isoformat(),
                            bookmaker="nike_sk",
                            home_odds=home_odds,
                            away_odds=away_odds
                        )
                        
                        games.append(game)
                        
                    except Exception as e:
                        # Skip games that fail to parse
                        continue
                
                browser.close()
                
                print(f"Successfully scraped {len(games)} games from Nike.sk")
                return games
                
        except Exception as e:
            print(f"Error scraping Nike.sk: {e}")
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
