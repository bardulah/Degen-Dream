"""League and sport selection strategy for agent analysis."""

from typing import List, Dict, Tuple, Optional
from enum import Enum


class AgentProfile(Enum):
    """Agent profiles for sport/league selection."""
    SHARP = "sharp"          # Wants: low-variance, liquid, high-edge markets
    INSIDER = "insider"      # Wants: injury info available, league news
    DEGEN = "degen"          # Wants: high-volume, volatile action
    BOOKIE = "bookie"        # Wants: public money trends, popular leagues


class LeagueConfig:
    """Configuration for a sports league."""
    
    def __init__(
        self,
        key: str,
        sport: str,
        name: str,
        region: str,
        liquidity: int,  # 1-5 (5=highest)
        public_volume: int,  # 1-5 (5=most bets)
        injury_info: int,  # 1-5 (5=best info)
        line_stability: int,  # 1-5 (5=most stable)
        market_efficiency: int,  # 1-5 (5=most efficient)
        best_for: List[AgentProfile]
    ):
        """Initialize league configuration.
        
        Args:
            key: API key for league (e.g., 'soccer_epl')
            sport: Sport type (soccer, basketball, hockey, tennis)
            name: Human-readable name
            region: Region for odds (eu, us, uk, au)
            liquidity: Bookmaker liquidity (1-5)
            public_volume: Expected public betting volume (1-5)
            injury_info: Availability of injury data (1-5)
            line_stability: How stable lines are (1-5)
            market_efficiency: How efficient market is (1-5)
            best_for: Agent types that benefit most from this league
        """
        self.key = key
        self.sport = sport
        self.name = name
        self.region = region
        self.liquidity = liquidity
        self.public_volume = public_volume
        self.injury_info = injury_info
        self.line_stability = line_stability
        self.market_efficiency = market_efficiency
        self.best_for = best_for
    
    def get_score_for_agent(self, agent_type: AgentProfile) -> float:
        """Calculate league suitability score for an agent type (0-100).
        
        Args:
            agent_type: Type of agent
        
        Returns:
            Score 0-100 (higher = better fit)
        """
        base_score = 0
        
        if agent_type == AgentProfile.SHARP:
            # Sharps want: liquidity, line stability, market efficiency
            base_score = (self.liquidity * 0.5 + 
                         self.line_stability * 0.3 + 
                         self.market_efficiency * 0.2) * 20
        
        elif agent_type == AgentProfile.INSIDER:
            # Insiders want: injury info, public volume, league coverage
            base_score = (self.injury_info * 0.4 + 
                         self.public_volume * 0.3 + 
                         self.liquidity * 0.3) * 20
        
        elif agent_type == AgentProfile.DEGEN:
            # Degens want: high volume, volatility (inverse stability), liquidity
            base_score = (self.public_volume * 0.4 + 
                         (6 - self.line_stability) * 0.3 +  # Inverse: chaos = good
                         self.liquidity * 0.3) * 20
        
        elif agent_type == AgentProfile.BOOKIE:
            # Bookies want: public volume, line movement opportunities, low efficiency
            base_score = (self.public_volume * 0.5 + 
                         (6 - self.market_efficiency) * 0.3 +  # Inverse: inefficiency = opportunity
                         self.liquidity * 0.2) * 20
        
        # Bonus if league is in agent's best_for list
        if agent_type in self.best_for:
            base_score *= 1.2
        
        return min(100, base_score)


class LeagueSelector:
    """Selects best leagues for agent analysis based on agent composition."""
    
    # Tier 1: Top liquidity, reliable, high volume (sharps love these)
    TIER_1_LEAGUES = [
        LeagueConfig(
            key="soccer_epl",
            sport="soccer",
            name="English Premier League",
            region="eu",
            liquidity=5, public_volume=5, injury_info=5, line_stability=5, market_efficiency=5,
            best_for=[AgentProfile.SHARP, AgentProfile.BOOKIE]
        ),
        LeagueConfig(
            key="soccer_spain_la_liga",
            sport="soccer",
            name="Spanish La Liga",
            region="eu",
            liquidity=5, public_volume=5, injury_info=5, line_stability=4, market_efficiency=5,
            best_for=[AgentProfile.SHARP, AgentProfile.INSIDER]
        ),
        LeagueConfig(
            key="soccer_germany_bundesliga",
            sport="soccer",
            name="German Bundesliga",
            region="eu",
            liquidity=5, public_volume=4, injury_info=4, line_stability=4, market_efficiency=4,
            best_for=[AgentProfile.SHARP, AgentProfile.INSIDER]
        ),
        LeagueConfig(
            key="soccer_italy_serie_a",
            sport="soccer",
            name="Italian Serie A",
            region="eu",
            liquidity=5, public_volume=4, injury_info=4, line_stability=4, market_efficiency=4,
            best_for=[AgentProfile.SHARP, AgentProfile.DEGEN]
        ),
        LeagueConfig(
            key="soccer_france_ligue_1",
            sport="soccer",
            name="French Ligue 1",
            region="eu",
            liquidity=4, public_volume=3, injury_info=3, line_stability=3, market_efficiency=4,
            best_for=[AgentProfile.INSIDER, AgentProfile.DEGEN]
        ),
        LeagueConfig(
            key="basketball_nba",
            sport="basketball",
            name="NBA (North America)",
            region="us",
            liquidity=5, public_volume=5, injury_info=5, line_stability=3, market_efficiency=4,
            best_for=[AgentProfile.SHARP, AgentProfile.BOOKIE, AgentProfile.DEGEN]
        ),
    ]
    
    # Tier 2: Solid options, good for diversity (insiders/degens benefit)
    TIER_2_LEAGUES = [
        LeagueConfig(
            key="basketball_euroleague",
            sport="basketball",
            name="EuroLeague Basketball",
            region="eu",
            liquidity=3, public_volume=2, injury_info=2, line_stability=3, market_efficiency=3,
            best_for=[AgentProfile.INSIDER, AgentProfile.DEGEN]
        ),
        LeagueConfig(
            key="hockey_nhl",
            sport="hockey",
            name="NHL (North America)",
            region="us",
            liquidity=4, public_volume=4, injury_info=4, line_stability=4, market_efficiency=4,
            best_for=[AgentProfile.SHARP, AgentProfile.DEGEN]
        ),
        LeagueConfig(
            key="tennis_atp",
            sport="tennis",
            name="ATP Tennis",
            region="eu",
            liquidity=3, public_volume=2, injury_info=3, line_stability=2, market_efficiency=3,
            best_for=[AgentProfile.INSIDER, AgentProfile.DEGEN]
        ),
        LeagueConfig(
            key="tennis_wta",
            sport="tennis",
            name="WTA Tennis",
            region="eu",
            liquidity=2, public_volume=2, injury_info=3, line_stability=2, market_efficiency=2,
            best_for=[AgentProfile.DEGEN]
        ),
    ]
    
    # Tier 3: Niche/lower liquidity (good for degens, risky for sharps)
    TIER_3_LEAGUES = [
        LeagueConfig(
            key="soccer_netherlands_eredivisie",
            sport="soccer",
            name="Dutch Eredivisie",
            region="eu",
            liquidity=3, public_volume=2, injury_info=2, line_stability=2, market_efficiency=2,
            best_for=[AgentProfile.DEGEN, AgentProfile.INSIDER]
        ),
        LeagueConfig(
            key="soccer_portugal_primeira_liga",
            sport="soccer",
            name="Portuguese Primeira Liga",
            region="eu",
            liquidity=2, public_volume=1, injury_info=1, line_stability=2, market_efficiency=2,
            best_for=[AgentProfile.DEGEN]
        ),
    ]
    
    ALL_LEAGUES = TIER_1_LEAGUES + TIER_2_LEAGUES + TIER_3_LEAGUES
    
    @classmethod
    def get_leagues_for_agent_composition(
        cls,
        num_sharps: int = 3,
        num_insiders: int = 2,
        num_degens: int = 3,
        num_bookies: int = 2,
        max_leagues: int = 8,
        prefer_tiers: str = "1+2"  # "1" = only top, "1+2" = top+mid, "all" = everything
    ) -> List[LeagueConfig]:
        """Select optimal leagues based on agent composition.
        
        Strategy:
        - Sharps + Bookies: Include max Tier 1 (top leagues, tight markets)
        - Insiders: Include leagues with good injury/news coverage
        - Degens: Include diverse, chaotic markets (Tier 2-3, off-hours)
        - Goal: Balance depth (few leagues, many games) vs breadth (many sports)
        
        Args:
            num_sharps: Number of sharp agents
            num_insiders: Number of insider agents
            num_degens: Number of degen agents
            num_bookies: Number of bookie agents
            max_leagues: Maximum leagues to select
            prefer_tiers: Which tiers to include ("1", "1+2", "all")
        
        Returns:
            Ranked list of LeagueConfig objects
        """
        # Determine agent distribution
        total_agents = num_sharps + num_insiders + num_degens + num_bookies
        sharp_pct = num_sharps / total_agents if total_agents > 0 else 0.3
        insider_pct = num_insiders / total_agents if total_agents > 0 else 0.2
        degen_pct = num_degens / total_agents if total_agents > 0 else 0.3
        bookie_pct = num_bookies / total_agents if total_agents > 0 else 0.2
        
        # Build weighted preference
        weighted_scores = {}
        for league in cls.ALL_LEAGUES:
            score = (
                cls._get_profile_score(league, AgentProfile.SHARP) * sharp_pct +
                cls._get_profile_score(league, AgentProfile.INSIDER) * insider_pct +
                cls._get_profile_score(league, AgentProfile.DEGEN) * degen_pct +
                cls._get_profile_score(league, AgentProfile.BOOKIE) * bookie_pct
            )
            weighted_scores[league] = score
        
        # Filter by tier preference
        if prefer_tiers == "1":
            candidates = cls.TIER_1_LEAGUES
        elif prefer_tiers == "1+2":
            candidates = cls.TIER_1_LEAGUES + cls.TIER_2_LEAGUES
        else:
            candidates = cls.ALL_LEAGUES
        
        # Sort by weighted score (descending)
        ranked = sorted(
            [l for l in candidates if l in weighted_scores],
            key=lambda l: weighted_scores[l],
            reverse=True
        )
        
        return ranked[:max_leagues]
    
    @classmethod
    def _get_profile_score(cls, league: LeagueConfig, profile: AgentProfile) -> float:
        """Get score for a single agent profile on a league."""
        return league.get_score_for_agent(profile)
    
    @classmethod
    def get_sports_with_available_games(
        cls,
        leagues: List[LeagueConfig]
    ) -> Dict[str, List[LeagueConfig]]:
        """Group selected leagues by sport.
        
        Args:
            leagues: List of leagues to group
        
        Returns:
            Dict mapping sport name to list of leagues
        """
        sports = {}
        for league in leagues:
            if league.sport not in sports:
                sports[league.sport] = []
            sports[league.sport].append(league)
        return sports
    
    @classmethod
    def recommend_league_selection(
        cls,
        num_sharps: int = 3,
        num_insiders: int = 2,
        num_degens: int = 3,
        num_bookies: int = 2
    ) -> Dict[str, any]:
        """Generate a full recommendation for league selection.
        
        Returns:
            Dict with selected_leagues, sports, reasoning
        """
        leagues = cls.get_leagues_for_agent_composition(
            num_sharps, num_insiders, num_degens, num_bookies,
            prefer_tiers="1+2"
        )
        
        sports = cls.get_sports_with_available_games(leagues)
        
        reasoning = {
            "agents": {
                "sharps": num_sharps,
                "insiders": num_insiders,
                "degens": num_degens,
                "bookies": num_bookies
            },
            "strategy": f"Prioritized Tier 1 for sharps/bookies, mixed tiers for degens/insiders",
            "expected_game_volume": f"~{sum(max(1, (5-l.liquidity)*2) for l in leagues)} games daily",
            "diversity": f"{len(sports)} sports: {', '.join(sports.keys())}"
        }
        
        return {
            "selected_leagues": leagues,
            "sports": sports,
            "reasoning": reasoning,
            "league_details": [
                {
                    "name": l.name,
                    "sport": l.sport,
                    "key": l.key,
                    "best_for": [p.value for p in l.best_for],
                    "scores": {
                        "sharp": round(l.get_score_for_agent(AgentProfile.SHARP), 1),
                        "insider": round(l.get_score_for_agent(AgentProfile.INSIDER), 1),
                        "degen": round(l.get_score_for_agent(AgentProfile.DEGEN), 1),
                        "bookie": round(l.get_score_for_agent(AgentProfile.BOOKIE), 1),
                    }
                }
                for l in leagues
            ]
        }


if __name__ == "__main__":
    # Test league recommendation
    rec = LeagueSelector.recommend_league_selection()
    
    print("=" * 70)
    print("LEAGUE SELECTION RECOMMENDATION")
    print("=" * 70)
    print(f"\nAgent Composition: {rec['reasoning']['agents']}")
    print(f"Strategy: {rec['reasoning']['strategy']}")
    print(f"Diversity: {rec['reasoning']['diversity']}")
    
    print("\n" + "=" * 70)
    print("SELECTED LEAGUES")
    print("=" * 70)
    for detail in rec['league_details']:
        print(f"\n📊 {detail['name']} ({detail['sport'].upper()})")
        print(f"   API Key: {detail['key']}")
        print(f"   Best For: {', '.join(detail['best_for'])}")
        print(f"   Scores: Sharp={detail['scores']['sharp']}, "
              f"Insider={detail['scores']['insider']}, "
              f"Degen={detail['scores']['degen']}, "
              f"Bookie={detail['scores']['bookie']}")
