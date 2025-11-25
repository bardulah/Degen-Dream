
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.base_agent import Bet, Game, AgentType
from simulation.graph import run_simulation, SyndicateGraph

@pytest.fixture
def mock_settings(mocker):
    mocker.patch('config.settings.settings.ANTHROPIC_API_KEY', 'dummy_key')
    mocker.patch('config.settings.settings.validate', return_value=True)

@pytest.fixture
def mock_anthropic(mocker):
    mock_client = MagicMock()
    mocker.patch('agents.base_agent.Anthropic', return_value=mock_client)
    return mock_client

@pytest.fixture
def sample_games():
    return [
        Game(
            id="1",
            home_team="Team A",
            away_team="Team B",
            sport="soccer_epl",
            commence_time="2023-01-01T12:00:00Z",
            bookmaker="pinnacle",
            home_odds=2.0,
            away_odds=3.0,
            over_odds=1.9,
            under_odds=1.9
        ),
        Game(
            id="2",
            home_team="Team C",
            away_team="Team D",
            sport="soccer_epl",
            commence_time="2023-01-01T14:00:00Z",
            bookmaker="pinnacle",
            home_odds=1.5,
            away_odds=4.0
        )
    ]

def test_simulation_flow(mock_settings, mock_anthropic, sample_games, mocker):
    # Mock analyze_game for all agents to avoid LLM calls
    # We need to patch the analyze_game method of the specific agent classes or BaseAgent if they inherit it
    # Since we don't know exactly which agents are used (default ones), we can patch the classes.
    
    # Let's patch BaseAgent.analyze_game, but wait, subclasses override it.
    # So we should patch the subclasses or the instances.
    # Easier to patch SyndicateGraph._create_default_agents to return mocked agents.
    
    mock_agent = MagicMock()
    mock_agent.name = "MockAgent"
    mock_agent.agent_type = AgentType.SHARP
    mock_agent.bankroll = 1000.0
    mock_agent.initial_bankroll = 1000.0
    mock_agent.get_stats.return_value = {
        "name": "MockAgent",
        "type": "sharp",
        "bankroll": 1000.0,
        "roi": 0.0,
        "total_bets": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0,
        "profit_loss": 0
    }
    
    # Mock analyze_game to return a bet sometimes
    mock_bet = Bet(
        game_id="1",
        team="Team A",
        bet_type="moneyline",
        line=0.0,
        odds=2.0,
        stake=50.0,
        confidence=0.8,
        reasoning="Mock reasoning",
        agent_name="MockAgent"
    )
    
    mock_agent.analyze_game.return_value = mock_bet
    mock_agent.debate.return_value = "I agree with myself."
    
    # Patch SyndicateGraph to use our mock agents
    with patch.object(SyndicateGraph, '_create_default_agents', return_value=[mock_agent]):
        results = run_simulation(games=sample_games, num_games=2, starting_bankroll=10000)
        
        assert results is not None
        assert "stats" in results
        assert "agent_stats" in results
        assert len(results["results"]) > 0
        assert results["stats"]["total_bets"] > 0

