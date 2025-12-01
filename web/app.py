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
from simulation.graph import SyndicateGraph, evaluate_simulation_bets
from agents.base_agent import Game
from database.schema import (
    SessionLocal, Simulation, Bet, AgentSimulationStats,
    User, init_db
)
from database.auth import auth_manager, UserTier
import uuid

# Get the directory where app.py is located
web_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            static_folder=web_dir,
            template_folder=os.path.join(web_dir, 'templates'))
app.config['SECRET_KEY'] = 'bratislava-betting-syndicate-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Database
init_db()

# Global state for current simulation
current_simulation = {
    'running': False,
    'simulation_id': None,
    'current_game': None,
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

    def show_bet_evaluation(self, evaluation: Dict):
        """Emit bet evaluation results to dashboard."""
        self.socketio.emit('bet_evaluation', {
            'total_bets': evaluation.get('total_bets', 0),
            'matched_bets': evaluation.get('matched_bets', 0),
            'unmatched_bets': evaluation.get('unmatched_bets', 0),
            'wins': evaluation.get('wins', 0),
            'losses': evaluation.get('losses', 0),
            'win_rate': evaluation.get('win_rate', 0.0),
            'total_staked': evaluation.get('total_staked', 0.0),
            'total_profit_loss': evaluation.get('total_profit_loss', 0.0),
            'roi': evaluation.get('roi', 0.0),
            'bet_results': [
                {
                    'home_team': bet.home_team,
                    'away_team': bet.away_team,
                    'bet_type': bet.bet_type,
                    'odds': bet.odds,
                    'stake': bet.stake,
                    'actual_home_score': bet.actual_home_score,
                    'actual_away_score': bet.actual_away_score,
                    'won': bet.won,
                    'profit_loss': bet.profit_loss
                }
                for bet in evaluation.get('bet_results', [])
            ]
        })


# Global game index
game_index = 0


def normalize_league_name(league: str) -> str:
    """Normalize league name for comparison.

    Handles both:
    - Original format: "ENGLAND: Premier League"
    - Pre-normalized format: "england_ premier_league"
    - Scraper format: "england_ premier_league" (with non-breaking spaces)
    """
    if not league:
        return ""

    # Convert to string and lowercase
    normalized = str(league).lower()
    
    # Explicitly replace non-breaking spaces and colons
    normalized = normalized.replace('\xa0', '_').replace(':', '')

    # Replace spaces and hyphens with underscores
    import re
    normalized = re.sub(r'[\s\-_]+', '_', normalized)

    # Strip leading/trailing underscores
    return normalized.strip("_")


def filter_games_by_leagues(games: List[Game], selected_leagues: List[str]) -> List[Game]:
    """Filter games by selected league names.

    Args:
        games: List of Game objects
        selected_leagues: List of league names (can be normalized or original format)

    Returns:
        Filtered list of games matching the selected leagues
    """
    if not selected_leagues or not games:
        return games

    # Normalize the selected league names
    normalized_selected = {normalize_league_name(league) for league in selected_leagues}

    # Filter games
    filtered = []
    for game in games:
        if hasattr(game, 'league') and game.league:
            normalized_game_league = normalize_league_name(game.league)
            if normalized_game_league in normalized_selected:
                filtered.append(game)

    return filtered


def run_simulation_background(num_games=1, starting_bankroll=10000, kelly_fraction=0.25, sport="multi", use_live_data=True, selected_leagues=None):
    """Run simulation in background and emit events."""
    global current_simulation, game_index

    # Create database session
    db = SessionLocal()

    try:
        current_simulation['running'] = True

        # Create user if not exists (for web dashboard)
        user_email = "web_dashboard@bratislava.local"
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = auth_manager.create_user(
                db=db,
                email=user_email,
                password="web_dashboard_2024",
                tier=UserTier.ENTERPRISE
            )

        # Create simulation record
        simulation_id = str(uuid.uuid4())
        simulation = Simulation(
            id=simulation_id,
            user_id=user.id,
            num_games=num_games,
            starting_bankroll=starting_bankroll,
            kelly_fraction=kelly_fraction,
            sport=sport if sport != "multi" else "multi-sport",
            use_live_data=use_live_data,
            status="in_progress",
            created_at=datetime.utcnow()
        )
        db.add(simulation)
        db.commit()

        current_simulation['simulation_id'] = simulation_id

        # Fetch games - use live Flashscore scraper or sample data
        from data.sample_games import get_sample_games, get_available_leagues
        from data.odds_aggregator import OddsAggregator

        if use_live_data:
            print(f"📊 Using LIVE data from Flashscore")
            print(f"  Sport requested: {sport}")

            # Get live games from Flashscore via aggregator
            aggregator = OddsAggregator()
            all_games = aggregator.get_all_odds(sport=sport)
            print(f"  Total live games: {len(all_games)}")
        else:
            print(f"📊 Using sample data mode")
            print(f"  Sport requested: {sport}")
            print(f"  Use live data: {use_live_data}")

            # Get all sample games
            all_games = get_sample_games()
            print(f"  Total sample games: {len(all_games)}")

        # Filter by sport if not multi
        if sport != 'multi':
            all_games = [g for g in all_games if g.sport == sport]
            print(f"  After sport filter ({sport}): {len(all_games)}")
            if all_games:
                sport_leagues = set(g.league for g in all_games if hasattr(g, 'league') and g.league)
                # Debug log available leagues
                print(f"  Leagues available: {sorted(list(sport_leagues))[:5]}...")

        # Filter by leagues if specified
        if selected_leagues:
            print(f"  Leagues requested: {selected_leagues}")
            print(f"  Games before league filter: {len(all_games)}")
            
            # DEBUG: Show some available leagues to debug matching
            available = set(g.league for g in all_games if hasattr(g, 'league'))
            
            all_games = filter_games_by_leagues(all_games, selected_leagues)
            print(f"  After league filter: {len(all_games)}")

            # Show which leagues were found
            found_leagues = set(g.league for g in all_games if g.league)
            print(f"  Leagues found in filtered games: {sorted(found_leagues)}")
            if all_games:
                print(f"  Found {len(all_games)} games for simulation")

        games = all_games

        if not games:
            msg = f'No {sport} games available'
            if selected_leagues:
                normalized_sel = [normalize_league_name(l) for l in selected_leagues]
                msg += f' in selected leagues: {", ".join(selected_leagues)}'
                # Add helpful debug info to console/log
                print(f"❌ DEBUG: Requested normalized: {normalized_sel}")
                if 'available' in locals() and available:
                    normalized_avail = [normalize_league_name(l) for l in list(available)[:5]]
                    print(f"❌ DEBUG: Available normalized (sample): {normalized_avail}")
            
            print(f"❌ {msg}")
            socketio.emit('notification', {
                'type': 'error',
                'message': msg
            })
            simulation.status = 'failed'
            simulation.error_message = msg
            db.commit()
            return

        print(f"  Final game count: {len(games)}")
        
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
        # Fix: Pass sport to SyndicateGraph so it creates correct agents
        syndicate = SyndicateGraph(sport=sport)
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
                # Save bet to database
                from database.schema import BetType as DBBetType

                bet_id = str(uuid.uuid4())
                game_date = datetime.now().strftime('%Y%m%d')  # Use today's date for now

                bet_record = Bet(
                    id=bet_id,
                    simulation_id=simulation_id,
                    agent_name=consensus_bet.agent_name,
                    game_home_team=game.home_team,
                    game_away_team=game.away_team,
                    sport=game.sport,
                    bet_team=consensus_bet.team,
                    bet_type=DBBetType.MONEYLINE if consensus_bet.bet_type == 'moneyline' else DBBetType.SPREAD,
                    line=0.0,  # Would need to extract from consensus_bet if available
                    odds=consensus_bet.odds,
                    stake=consensus_bet.stake,
                    confidence=consensus_bet.confidence,
                    reasoning=consensus_bet.reasoning if hasattr(consensus_bet, 'reasoning') else '',
                    game_date=game_date,
                    result_status='pending',
                    created_at=datetime.utcnow()
                )
                db.add(bet_record)
                db.commit()

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
                    print("Real Mode: Bet placed. Waiting for match result...")
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

                # Update agent stats in database
                agent_stats_record = db.query(AgentSimulationStats).filter(
                    AgentSimulationStats.simulation_id == simulation_id,
                    AgentSimulationStats.agent_name == consensus_bet.agent_name
                ).first()

                if not agent_stats_record:
                    # Create agent stats record
                    for agent in syndicate.agents:
                        if agent.name == consensus_bet.agent_name:
                            agent_stats_record = AgentSimulationStats(
                                id=str(uuid.uuid4()),
                                simulation_id=simulation_id,
                                agent_name=agent.name,
                                agent_type=agent.agent_type,
                                initial_bankroll=agent.bankroll,
                                final_bankroll=agent.bankroll,
                                roi=0.0,
                                total_bets=0,
                                wins=0,
                                losses=0,
                                win_rate=0.0,
                                profit_loss=0.0
                            )
                            db.add(agent_stats_record)
                            db.commit()
                            break

                # Update bet record with simulated result
                if is_win:
                    bet_record.result_status = 'won'
                    bet_record.profit_loss = profit
                else:
                    bet_record.result_status = 'lost'
                    bet_record.profit_loss = -consensus_bet.stake

                bet_record.result_fetched_at = datetime.utcnow()
                db.commit()

                # Update agent stats record
                if agent_stats_record:
                    if is_win:
                        agent_stats_record.wins += 1
                    else:
                        agent_stats_record.losses += 1

                    agent_stats_record.total_bets += 1
                    agent_stats_record.profit_loss = (agent_stats_record.profit_loss or 0) + (profit if is_win else -consensus_bet.stake)

                    # Recalculate stats
                    total_bets_count = agent_stats_record.total_bets
                    wins_count = agent_stats_record.wins
                    agent_stats_record.win_rate = (wins_count / total_bets_count * 100) if total_bets_count > 0 else 0.0

                    # Calculate ROI
                    total_wagered = consensus_bet.stake * total_bets_count
                    agent_stats_record.roi = (agent_stats_record.profit_loss / total_wagered * 100) if total_wagered > 0 else 0.0

                    agent_stats_record.final_bankroll = agent_stats_record.initial_bankroll + agent_stats_record.profit_loss
                    db.commit()

                # Update simulation stats
                simulation.final_bankroll = syndicate.bankroll_manager.current_bankroll
                simulation.profit = syndicate.bankroll_manager.current_bankroll - syndicate.bankroll_manager.initial_bankroll
                simulation.roi = (simulation.profit / simulation.starting_bankroll * 100) if simulation.starting_bankroll > 0 else 0.0
                simulation.total_bets = db.query(Bet).filter(Bet.simulation_id == simulation_id).count()
                simulation.bets_settled = db.query(Bet).filter(
                    Bet.simulation_id == simulation_id,
                    Bet.result_status.in_(['won', 'lost'])
                ).count()
                db.commit()

                stats_data = {
                    'bankroll': syndicate.bankroll_manager.current_bankroll,
                    'pnl': simulation.profit,
                    'roi': simulation.roi,
                    'win_rate': 0.0,
                    'exposure': 0.0,
                    'agent_stats': syndicate.get_agent_stats()
                }

                socketio.emit('stats_update', stats_data)

            else:
                monitor.show_error("No consensus reached - Pass")

            # Pause between games
            socketio.sleep(3)

        # Evaluate bets against actual results
        monitor.show_success("🎯 Evaluating bets against actual match results...")

        # Get all bets from this simulation
        sim_bets = db.query(Bet).filter(Bet.simulation_id == simulation_id).all()

        if sim_bets:
            # Convert database bets to evaluation format
            bets_for_evaluation = []
            for bet in sim_bets:
                # Determine bet_type based on bet_team
                if bet.bet_team == bet.game_home_team:
                    bet_type = 'home'
                elif bet.bet_team == bet.game_away_team:
                    bet_type = 'away'
                else:
                    bet_type = 'draw'

                bets_for_evaluation.append({
                    'id': bet.id,
                    'home_team': bet.game_home_team,
                    'away_team': bet.game_away_team,
                    'bet_type': bet_type,
                    'odds': bet.odds,
                    'stake': bet.stake
                })

            # Evaluate bets (this fetches finished matches from Flashscore)
            evaluation = evaluate_simulation_bets(
                [{'home_team': b['home_team'], 'away_team': b['away_team'],
                  'prediction': b['bet_type'], 'odds': b['odds'], 'stake': b['stake'],
                  'game_id': b['id']} for b in bets_for_evaluation],
                sport=sport if sport != 'multi' else 'soccer',
                monitor=monitor
            )

            if evaluation:
                # Emit evaluation results to dashboard
                monitor.show_bet_evaluation(evaluation)

                # Update bet records with actual results
                for bet_result in evaluation.get('bet_results', []):
                    # Find matching bet in database
                    for db_bet in sim_bets:
                        if (db_bet.game_home_team == bet_result.home_team and
                            db_bet.game_away_team == bet_result.away_team):
                            # Update bet with actual result
                            db_bet.result_status = 'won' if bet_result.won else 'lost'
                            db_bet.profit_loss = bet_result.profit_loss  # Using existing column
                            db_bet.home_score = bet_result.actual_home_score  # Using existing column
                            db_bet.away_score = bet_result.actual_away_score  # Using existing column
                            db_bet.result_fetched_at = datetime.utcnow()
                            break

                db.commit()

                monitor.show_success(f"✅ Evaluation complete! {evaluation['wins']}W-{evaluation['losses']}L | ROI: {evaluation['roi']:+.1f}%")
                simulation.status = 'completed'  # All results evaluated
            else:
                monitor.show_warning("⚠️  Could not evaluate bets - no finished matches found")
                simulation.status = 'awaiting_results'  # Still waiting for real results
        else:
            simulation.status = 'completed'  # No bets to evaluate

        simulation.duration_seconds = int((datetime.utcnow() - simulation.created_at).total_seconds())
        db.commit()

    except Exception as e:
        import traceback
        traceback.print_exc()
        socketio.emit('notification', {
            'type': 'error',
            'message': f'Simulation error: {str(e)}'
        })

        # Mark simulation as failed
        if 'simulation' in locals():
            simulation.status = 'failed'
            simulation.error_message = str(e)
            db.commit()

    finally:
        current_simulation['running'] = False
        db.close()


@app.route('/')
def index():
    """Serve the dashboard."""
    return render_template('dashboard.html')


@app.route('/enhanced')
def enhanced():
    """Serve the enhanced dashboard with league selection and agent composition."""
    return render_template('enhanced_dashboard.html')


@app.route('/fixed')
def fixed():
    """Serve the fixed dashboard with working league selection and scroll fixes."""
    return render_template('fixed_dashboard.html')


@app.route('/scrollable')
def scrollable():
    """Serve the scrollable dashboard with proper terminal scrolling."""
    return render_template('scrollable_dashboard.html')


@app.route('/ultimate')
def ultimate():
    """Serve the ultimate dashboard with working league selection and scrollable terminal."""
    return render_template('ultimate_dashboard.html')


@app.route('/api/status')
def status():
    """Get current simulation status."""
    if current_simulation.get('simulation_id'):
        # Load from database
        db = SessionLocal()
        try:
            sim = db.query(Simulation).filter(
                Simulation.id == current_simulation['simulation_id']
            ).first()

            if sim:
                # Get bets
                bets = db.query(Bet).filter(
                    Bet.simulation_id == sim.id
                ).order_by(Bet.created_at.desc()).limit(20).all()

                # Get agent stats
                agent_stats = db.query(AgentSimulationStats).filter(
                    AgentSimulationStats.simulation_id == sim.id
                ).all()

                return jsonify({
                    'running': current_simulation['running'],
                    'simulation_id': sim.id,
                    'current_game': current_simulation.get('current_game'),
                    'stats': {
                        'total_bankroll': sim.final_bankroll or sim.starting_bankroll,
                        'roi': sim.roi or 0,
                        'win_rate': sim.win_rate or 0,
                        'total_bets': sim.total_bets or 0,
                        'bets_settled': sim.bets_settled or 0
                    },
                    'bets': [
                        {
                            'agent': b.agent_name,
                            'team': b.bet_team,
                            'bet_type': b.bet_type.value,
                            'stake': b.stake,
                            'odds': b.odds,
                            'result_status': b.result_status,
                            'profit_loss': b.profit_loss
                        }
                        for b in bets
                    ],
                    'agent_stats': [
                        {
                            'name': a.agent_name,
                            'type': a.agent_type,
                            'roi': a.roi,
                            'win_rate': a.win_rate,
                            'bankroll': a.final_bankroll,
                            'total_bets': a.total_bets,
                            'wins': a.wins,
                            'losses': a.losses
                        }
                        for a in agent_stats
                    ]
                })
        finally:
            db.close()

    return jsonify(current_simulation)


@app.route('/api/leagues/<sport>')
def get_available_leagues(sport):
    """Get available leagues for a sport by fetching live games."""
    try:
        from data.odds_aggregator import OddsAggregator

        aggregator = OddsAggregator()
        games = aggregator.get_all_odds(sport=sport)

        # Extract unique leagues
        leagues = set()
        for game in games:
            if hasattr(game, 'league') and game.league:
                leagues.add(game.league)

        return jsonify({
            'sport': sport,
            'leagues': sorted(list(leagues)),
            'total_games': len(games)
        })
    except Exception as e:
        return jsonify({'error': str(e), 'leagues': []}), 500


@app.route('/api/simulations/latest')
def get_latest_simulation():
    """Get the latest simulation data."""
    db = SessionLocal()
    try:
        sim = db.query(Simulation).order_by(Simulation.created_at.desc()).first()

        if not sim:
            return jsonify({'error': 'No simulations found'}), 404

        # Get bets
        bets = db.query(Bet).filter(
            Bet.simulation_id == sim.id
        ).order_by(Bet.created_at.desc()).all()

        # Get agent stats
        agent_stats = db.query(AgentSimulationStats).filter(
            AgentSimulationStats.simulation_id == sim.id
        ).all()

        return jsonify({
            'simulation_id': sim.id,
            'created_at': sim.created_at.isoformat(),
            'status': sim.status,
            'stats': {
                'total_bankroll': sim.final_bankroll or sim.starting_bankroll,
                'roi': sim.roi or 0,
                'win_rate': sim.win_rate or 0,
                'total_bets': sim.total_bets or 0,
                'bets_settled': sim.bets_settled or 0,
                'starting_bankroll': sim.starting_bankroll
            },
            'bets': [
                {
                    'id': b.id,
                    'agent': b.agent_name,
                    'team': b.bet_team,
                    'bet_type': b.bet_type.value,
                    'stake': b.stake,
                    'odds': b.odds,
                    'home_team': b.game_home_team,
                    'away_team': b.game_away_team,
                    'result_status': b.result_status,
                    'profit_loss': b.profit_loss,
                    'home_score': b.home_score,
                    'away_score': b.away_score
                }
                for b in bets
            ],
            'agent_stats': [
                {
                    'name': a.agent_name,
                    'type': a.agent_type,
                    'roi': a.roi or 0,
                    'win_rate': a.win_rate or 0,
                    'bankroll': a.final_bankroll or a.initial_bankroll,
                    'total_bets': a.total_bets,
                    'wins': a.wins,
                    'losses': a.losses
                }
                for a in agent_stats
            ]
        })
    finally:
        db.close()


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

    # Extract configuration from frontend
    num_games = data.get('num_games', 10)
    starting_bankroll = data.get('starting_bankroll', 10000)
    kelly_fraction = data.get('kelly_fraction', 0.25)
    sport = data.get('sport', 'multi')
    use_live_data = data.get('use_live_data', True)
    selected_leagues = data.get('selected_leagues', None)  # List of league names

    # Run in background thread
    thread = threading.Thread(
        target=run_simulation_background,
        args=(num_games, starting_bankroll, kelly_fraction, sport, use_live_data, selected_leagues)
    )
    thread.daemon = True
    thread.start()

    emit('notification', {
        'type': 'success',
        'message': f'Starting simulation: {num_games} games, €{starting_bankroll} bankroll, Kelly: {kelly_fraction}'
    })


@socketio.on('stop_simulation')
def handle_stop_simulation():
    """Stop the current simulation."""
    if not current_simulation['running']:
        emit('notification', {
            'type': 'warning',
            'message': 'No simulation running'
        })
        return

    current_simulation['running'] = False
    emit('notification', {
        'type': 'info',
        'message': 'Simulation stopped'
    })


if __name__ == '__main__':
    print("🎰 Starting Bratislava Betting Syndicate Dashboard...")
    print("📊 Dashboard: http://localhost:8508")
    socketio.run(app, host='0.0.0.0', port=8508, debug=False, allow_unsafe_werkzeug=True)
