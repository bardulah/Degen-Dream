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
            'draw_odds': game.draw_odds,
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

    def log_event(self, level: str, message: str):
        """Log an event to the dashboard."""
        # Map log levels to notification types if needed, or just send as info
        msg_type = 'info'
        if level.upper() == 'ERROR':
            msg_type = 'error'
        elif level.upper() == 'WARNING':
            msg_type = 'warning'
        elif level.upper() == 'SUCCESS':
            msg_type = 'success'
            
        self.socketio.emit('notification', {
            'type': msg_type,
            'message': message
        })

    def show_warning(self, message: str):
        """Emit warning message."""
        self.socketio.emit('notification', {
            'type': 'warning',
            'message': message
        })

    def show_separator(self):
        """Emit a separator (optional, maybe just a log line or ignored)."""
        # For the web dashboard, we might not need a visual separator, 
        # or we could emit a specific event if we wanted to draw a line.
        # For now, we'll just log a small break or ignore it to prevent errors.
        pass


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
        try:
            from data.gemini_search import GeminiSearchClient
            search_client = GeminiSearchClient()
        except Exception as e:
            print(f"Search client init failed: {e}")
            search_client = None
        
        # Run simulation
        syndicate = SyndicateGraph()
        syndicate.monitor = monitor
        
        for i in range(num_games):
            if not current_simulation['running']:
                break
                
            # Select next game using global index
            game = games[game_index % len(games)]
            game_index += 1
            
            # Emit game
            monitor.show_game(game)
            current_simulation['current_game'] = {
                'home_team': game.home_team,
                'away_team': game.away_team,
                'home_odds': game.home_odds,
                'away_odds': game.away_odds,
                'draw_odds': game.draw_odds
            }
            
            # Fetch Real-Time Context
            if search_client:
                monitor.show_success(f"🔍 Searching for latest news & squads for {game.home_team} vs {game.away_team}...")
                try:
                    context = search_client.get_match_context(game.home_team, game.away_team)
                    monitor.show_success("✅ Real-time data acquired")
                except Exception as e:
                    print(f"Search failed: {e}")
                    context = {}
            else:
                context = {}
            
            # Analyze game
            socketio.sleep(1)  # Brief pause
            state = syndicate.analyze_game(game, context)
            consensus_bet = state.get('consensus_bet')
            
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
                
                # Show success message
                monitor.show_success(f"✅ Bet Placed: {consensus_bet.bet_type} on {consensus_bet.team}")

                # --- SIMULATE RESULT ---
                # Check if we are in Demo Mode (Probabilistic) or Real Mode (Wait for Score)
                SIMULATION_DEMO_MODE = True  # Set to False to enable Real Score Checking (future feature)

                if SIMULATION_DEMO_MODE:
                    # Calculate implied probabilities from odds
                    # Margin is removed to normalize probabilities to sum to 1
                    
                    home_odds = game.home_odds
                    away_odds = game.away_odds
                    draw_odds = game.draw_odds if game.draw_odds else 0.0
                    
                    # Implied probabilities (1/odds)
                    prob_home = 1 / home_odds
                    prob_away = 1 / away_odds
                    prob_draw = 1 / draw_odds if draw_odds > 0 else 0.0
                    
                    total_prob = prob_home + prob_away + prob_draw
                    
                    # Normalize
                    norm_home = prob_home / total_prob
                    norm_away = prob_away / total_prob
                    norm_draw = prob_draw / total_prob
                    
                    # Roll the dice
                    import random
                    roll = random.random()
                    
                    winner = None
                    if roll < norm_home:
                        winner = game.home_team
                        winning_odds = home_odds
                    elif roll < (norm_home + norm_draw) and draw_odds > 0:
                        winner = "Draw"
                        winning_odds = draw_odds
                    else:
                        winner = game.away_team
                        winning_odds = away_odds
                    
                    # Determine Bet Outcome
                    is_win = False
                    if consensus_bet.bet_type == 'moneyline':
                        if consensus_bet.team == winner:
                            is_win = True
                    elif consensus_bet.bet_type == 'draw':
                        if winner == "Draw":
                            is_win = True
                    # TODO: Handle spread/total properly. For now, simplify:
                    # If spread, use 50/50 + edge. If total, 50/50.
                    elif consensus_bet.bet_type in ['spread', 'total']:
                         # Simple 50/50 for spread/total in this demo
                         is_win = random.random() < 0.5
                else:
                    # Real Mode: Wait for actual score
                    # In a real deployment, we would save the bet to a DB and check later.
                    # For now, we just log it.
                    monitor.log_event("INFO", "Real Mode: Bet placed. Waiting for match result...")
                    is_win = None # Pending
                
                # Update Bankroll Manager
                profit = 0
                if is_win:
                    profit = consensus_bet.stake * (consensus_bet.odds - 1)
                    syndicate.bankroll_manager.current_bankroll += (consensus_bet.stake + profit)
                    result_msg = f"🏆 WIN: {consensus_bet.team} won! (Result: {winner}) (+€{profit:.2f})"
                    monitor.show_success(result_msg)
                else:
                    syndicate.bankroll_manager.current_bankroll -= consensus_bet.stake 
                    result_msg = f"❌ LOSS: {consensus_bet.team} lost. (Result: {winner}) (-€{consensus_bet.stake:.2f})"
                    monitor.show_error(result_msg)

                # Update Global Stats
                current_bankroll = syndicate.bankroll_manager.current_bankroll
                start_bankroll = syndicate.bankroll_manager.initial_bankroll
                total_pnl = current_bankroll - start_bankroll
                roi = (total_pnl / start_bankroll) * 100
                
                # Update Agent Stats 
                for agent in syndicate.agents:
                    if agent.name == consensus_bet.agent_name:
                        if is_win:
                            agent.wins += 1
                            agent.bankroll += profit
                        else:
                            agent.losses += 1
                            agent.bankroll -= consensus_bet.stake
                
                stats_data = {
                    'bankroll': current_bankroll,
                    'pnl': total_pnl,
                    'roi': roi,
                    'win_rate': 0.0, 
                    'exposure': 0.0,
                    'agent_stats': syndicate.get_agent_stats() 
                }
                
                socketio.emit('stats_update', stats_data)
                
            else:
                monitor.show_error("No consensus reached - Pass")
            
            # Pause between games
            socketio.sleep(3)

    except Exception as e:
        import traceback
        traceback.print_exc()
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
