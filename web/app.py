"""Flask backend for live betting syndicate dashboard."""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
from typing import Dict, Any, List

from data.odds_aggregator import OddsAggregator
from simulation.graph import SyndicateGraph
from agents.base_agent import Game

# Get the directory where app.py is located
web_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            static_folder=web_dir,
            template_folder=os.path.join(web_dir, 'templates'))
app.config['SECRET_KEY'] = 'bratislava-betting-syndicate-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
current_simulation = {
    'running': False,
    'current_game': None,
    'agent_messages': [],
    'bets': [],
    'stats': {
        'total_bankroll': 10000,
        'roi': 0,
        'win_rate': 0,
        'total_bets': 0
    },
    'agent_stats': []
}


class DashboardMonitor:
    """Monitor that emits events to the dashboard via WebSocket."""
    
    def __init__(self, socketio):
        self.socketio = socketio
        
    def show_game(self, game: Game):
        """Emit current game to dashboard."""
        self.socketio.emit('new_game', {
            'home_team': game.home_team,
            'away_team': game.away_team,
            'sport': game.sport,
            'bookmaker': game.bookmaker,
            'home_odds': game.home_odds,
            'away_odds': game.away_odds,
            'commence_time': game.commence_time
        })
        
    def show_agent_response(self, agent_name: str, agent_type: str, 
                           response: str, decision: Dict = None):
        """Emit agent message to dashboard."""
        message = {
            'agent_name': agent_name,
            'agent_type': agent_type.lower(),
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        
        if decision:
            message['decision'] = decision
            
        self.socketio.emit('agent_message', message)
        
    def show_betting_slip(self, bets: List[Dict]):
        """Emit betting slip update."""
        self.socketio.emit('betting_slip', {'bets': bets})
        
    def show_agent_stats(self, stats: Dict):
        """Emit agent statistics."""
        self.socketio.emit('agent_stats', {'stats': stats})
        
    def show_success(self, message: str):
        """Emit success message."""
        self.socketio.emit('notification', {
            'type': 'success',
            'message': message
        })
        
    def show_error(self, message: str):
        """Emit error message."""
        self.socketio.emit('notification', {
            'type': 'error',
            'message': message
        })


# Global game index
game_index = 0

def run_simulation_background(num_games=1):
    """Run simulation in background and emit events."""
    global current_simulation, game_index
    
    try:
        current_simulation['running'] = True
        current_simulation['agent_messages'] = []
        current_simulation['bets'] = []
        
        # Fetch games
        aggregator = OddsAggregator()
        games = aggregator.get_all_odds()
        
        if not games:
            socketio.emit('notification', {
                'type': 'error',
                'message': 'No games available'
            })
            return
        
        # Create monitor
        monitor = DashboardMonitor(socketio)
        
        # Initialize Search Client
        search_client = GeminiSearchClient()
        
        # Run simulation
        syndicate = SyndicateGraph()
        syndicate.monitor = monitor
        
        # Select next game using global index
        game = games[game_index % len(games)]
        game_index += 1
        
        # Emit game
        monitor.show_game(game)
        current_simulation['current_game'] = {
            'home_team': game.home_team,
            'away_team': game.away_team,
            'home_odds': game.home_odds,
            'away_odds': game.away_odds
        }
        
        # Fetch Real-Time Context
        monitor.show_success(f"🔍 Searching for latest news & squads for {game.home_team} vs {game.away_team}...")
        try:
            context = search_client.get_match_context(game.home_team, game.away_team)
            monitor.show_success("✅ Real-time data acquired")
        except Exception as e:
            print(f"Search failed: {e}")
            context = {}
        
        # Analyze game
        time.sleep(1)  # Brief pause
        consensus_bet = syndicate.analyze_game(game, context)
        
        if consensus_bet:
            # Emit bet
            bet_data = {
                'agent': consensus_bet.agent_name,
                'team': consensus_bet.team,
                'bet_type': consensus_bet.bet_type,
                'stake': consensus_bet.stake,
                'odds': consensus_bet.odds,
                'confidence': consensus_bet.confidence
            }
            socketio.emit('new_bet', bet_data)
            
            # Show success message (without simulating result)
            monitor.show_success(f"✅ Bet Placed: {consensus_bet.bet_type} on {consensus_bet.team}")
        else:
            monitor.show_error("No consensus reached - Pass")
        
    except Exception as e:
        socketio.emit('notification', {
            'type': 'error',
            'message': f'Simulation error: {str(e)}'
        })
    finally:
        current_simulation['running'] = False


@app.route('/')
def index():
    """Serve the dashboard."""
    return render_template('dashboard.html')


@app.route('/api/status')
def status():
    """Get current simulation status."""
    return jsonify(current_simulation)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')
    emit('connected', {'message': 'Connected to Bratislava Betting Syndicate'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('Client disconnected')


@socketio.on('start_simulation')
def handle_start_simulation(data):
    """Start a new simulation."""
    if current_simulation['running']:
        emit('notification', {
            'type': 'warning',
            'message': 'Simulation already running'
        })
        return
    
    num_games = data.get('num_games', 5)
    
    # Run in background thread
    thread = threading.Thread(target=run_simulation_background, args=(num_games,))
    thread.daemon = True
    thread.start()
    
    emit('notification', {
        'type': 'success',
        'message': f'Starting simulation with {num_games} games...'
    })


if __name__ == '__main__':
    print("🎰 Starting Bratislava Betting Syndicate Dashboard...")
    print("📊 Dashboard: http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
