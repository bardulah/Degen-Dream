"""Python wrapper for Flashscore JavaScript scraper."""

import subprocess
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from agents.base_agent import Game


class FlashscoreWrapper:
    """Wrapper to run Flashscore JavaScript scraper from Python."""
    
    def __init__(self):
        """Initialize Flashscore wrapper."""
        self.script_path = os.path.join(
            os.path.dirname(__file__),
            'flashscore-scraper.js'
        )
        
    def get_odds(self, sport: str = 'football', limit: int = 50) -> List[Game]:
        """Get odds from Flashscore.
        
        Args:
            sport: Sport to scrape (football, basketball, tennis, hockey)
            limit: Maximum number of matches to return
            
        Returns:
            List of Game objects with odds
        """
        try:
            # Note: The JS scraper needs to be modified to accept CLI args
            # For now, we'll run it as-is and parse the output
            
            print(f"Running Flashscore scraper for {sport}...")
            
            # Run the Node.js scraper
            result = subprocess.run(
                ['node', self.script_path],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=os.path.dirname(self.script_path)
            )
            
            if result.returncode != 0:
                print(f"Flashscore scraper error: {result.stderr}")
                return []
            
            # Parse JSON output
            # The scraper should output JSON to stdout
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # If the scraper outputs logs, try to find JSON in the output
                lines = result.stdout.strip().split('\n')
                for line in reversed(lines):
                    try:
                        data = json.loads(line)
                        break
                    except:
                        continue
                else:
                    print("Could not parse Flashscore output as JSON")
                    return []
            
            # Convert to Game objects
            games = self._convert_to_games(data, sport)
            
            print(f"Successfully scraped {len(games)} games from Flashscore")
            return games[:limit]
            
        except subprocess.TimeoutExpired:
            print("Flashscore scraper timed out")
            return []
        except Exception as e:
            print(f"Error running Flashscore scraper: {e}")
            return []
    
    def _convert_to_games(self, data: Dict[str, Any], sport: str) -> List[Game]:
        """Convert Flashscore data to Game objects.
        
        Args:
            data: Raw data from Flashscore scraper
            sport: Sport type
            
        Returns:
            List of Game objects
        """
        games = []
        
        # Handle different data structures
        matches = data.get('matches', []) if isinstance(data, dict) else data
        
        for match in matches:
            try:
                # Extract odds from Flashscore bookmaker
                odds_data = match.get('odds', {})
                flashscore_odds = odds_data.get('Flashscore', {})
                
                if not flashscore_odds:
                    continue
                
                home_odds = flashscore_odds.get('home')
                away_odds = flashscore_odds.get('away')
                
                if not home_odds or not away_odds:
                    continue
                
                # Create Game object
                game = Game(
                    id=match.get('id', f"flashscore_{len(games)}"),
                    home_team=match.get('homeTeam', 'Unknown'),
                    away_team=match.get('awayTeam', 'Unknown'),
                    sport=match.get('sport', sport),
                    commence_time=match.get('date', datetime.now().isoformat()),
                    bookmaker='flashscore',
                    home_odds=float(home_odds),
                    away_odds=float(away_odds)
                )
                
                games.append(game)
                
            except Exception as e:
                print(f"Error converting Flashscore match: {e}")
                continue
        
        return games


# Test function
if __name__ == "__main__":
    wrapper = FlashscoreWrapper()
    games = wrapper.get_odds('football')
    
    print(f"\nFound {len(games)} games:")
    for i, game in enumerate(games[:5], 1):
        print(f"{i}. {game.home_team} vs {game.away_team}")
        print(f"   Odds: {game.home_odds} / {game.away_odds}")
